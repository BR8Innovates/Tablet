/**
 * Issue a policy from a proposal. Request: { "ProposalNo": "...", "ProductCode": "..." }.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.proposal.ProposalSdkClient

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPShaper shaper = (UPShaper) getCommonService("UPShaper")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPIssue", input)
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    UPNotify notify = (UPNotify) getCommonService("UPNotify")
    Map<String, Object> caller = access.require(Arrays.asList(util.cfg("RoleProposalChecker", "*")))
    String proposalNo = util.str(input.get("ProposalNo"))
    if (!proposalNo) {
        util.fail("ProposalNo is required")
    }
    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    Map<String, Object> existing = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder().proposalNo(proposalNo).doRequest().getBody()
    if (existing == null) {
        return errorHandler.notFound("UPIssue", "No proposal found for ${proposalNo}".toString())
    }
    validator.requireChannel(existing, util.str(input.get("ChannelCode")))
    validator.requireProductMatch(existing, util.str(input.get("ProductCode")), "")
    validator.requireOpenProposal(existing, "issued")
    access.requireNotCreator(caller, util.str(existing.get("AgentCode")))
    // optional recalculation (Recalculate = the configured TrueValue) so the stored premium factors match before issue
    if (util.isYes(input.get("Recalculate"))) {
        Map<String, Object> stored = (Map<String, Object>) proposalSdkClient.proposalApi()
                .newLoadRequestBuilder()
                .proposalNo(proposalNo)
                .doRequest()
                .getBody()
        proposalSdkClient.proposalApi().newPersistCalculateRequestBuilder().requestBody(stored).doRequest().getBody()
    }
    Map<String, Object> issueRequest = new HashMap<String, Object>()
    issueRequest.put("ProposalNo", proposalNo)
    Map<String, Object> response = (Map<String, Object>) proposalSdkClient.proposalApi()
            .newIssuePolicyRequestBuilder()
            .requestBody(issueRequest)
            .doRequest()
            .getBody()
    Map<String, Object> shaped = (Map<String, Object>) shaper.shapeResponse(response)
    List<Map<String, Object>> sent = notify.fire("PROPOSAL_ISSUED", notify.paramsOf(shaped, null), notify.customerOf(existing), util.str(existing.get("AgentCode")), "")
    shaped.put("Notifications", sent)
    return shaped

} catch (Exception ex) {
    return errorHandler.handle("UPIssue", ex)
}
