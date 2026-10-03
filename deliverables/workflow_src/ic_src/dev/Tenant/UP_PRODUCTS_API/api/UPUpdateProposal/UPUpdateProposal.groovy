/**
 * Update an existing proposal. ProposalNo is required; the policy identifiers are loaded from the stored proposal.
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
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    UPShaper shaper = (UPShaper) getCommonService("UPShaper")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPUpdateProposal", input)
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    Map<String, Object> caller = access.require(Arrays.asList(util.cfg("RoleMaker", "*")))
    String proposalNo = util.str(input.get("ProposalNo"))
    if (!proposalNo) {
        util.fail("ProposalNo is required")
    }
    Map<String, Object> payload = products.prepareProposal(input)

    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    Map<String, Object> stored = (Map<String, Object>) proposalSdkClient.proposalApi()
            .newLoadRequestBuilder()
            .proposalNo(proposalNo)
            .withCodeDesc(util.yes())
            .doRequest()
            .getBody()
    if (stored == null) {
        return errorHandler.notFound("UPUpdateProposal", "No proposal found for ${proposalNo}".toString())
    }
    validator.requireChannel(stored, util.str(input.get("ChannelCode")))
    validator.requireProductMatch(stored, util.str(input.get("ProductCode")), util.str(input.get("ProductSubcode")))
    validator.requireOpenProposal(stored, "updated")
    access.requireCreator(caller, util.str(stored.get("AgentCode")))
    payload.put("AgentCode", util.str(stored.get("AgentCode")) ?: caller.get("UserId"))
    payload.put("PolicyId", stored.get("PolicyId"))
    payload.put("PolicyElementId", stored.get("PolicyElementId"))
    payload.put("VersionSeq", stored.get("VersionSeq"))

    Map<String, Object> response = (Map<String, Object>) proposalSdkClient.proposalApi()
            .newSaveRequestBuilder()
            .requestBody(payload)
            .doRequest()
            .getBody()
    // the save drops the calculated plan row, so recalculate and persist to keep the premium factors consistent
    Map<String, Object> calculated = (Map<String, Object>) proposalSdkClient.proposalApi()
            .newPersistCalculateRequestBuilder()
            .requestBody(response)
            .doRequest()
            .getBody()
    return shaper.shapeResponse(calculated)

} catch (Exception ex) {
    return errorHandler.handle("UPUpdateProposal", ex)
}
