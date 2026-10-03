/**
 * Reject a proposal (checker action). Request: { "ProposalNo", "ProposalRejectDesc" }.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.proposal.ProposalSdkClient
import com.insuremo.sdk.services.proposal.model.RejectVo

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPProposalReject", input)
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
        return errorHandler.notFound("UPProposalReject", "No proposal found for ${proposalNo}".toString())
    }
    validator.requireChannel(existing, util.str(input.get("ChannelCode")))
    validator.requireProductMatch(existing, util.str(input.get("ProductCode")), "")
    validator.requireOpenProposal(existing, "rejected")
    access.requireNotCreator(caller, util.str(existing.get("AgentCode")))
    RejectVo rejectVo = new RejectVo()
    rejectVo.setProposalNo(proposalNo)
    rejectVo.setProposalRejectDesc(util.str(input.get("ProposalRejectDesc")))
    proposalSdkClient.proposalApi().newRejectRequestBuilder().rejectVo(rejectVo).doRequest()

    Map<String, Object> response = new HashMap<String, Object>()
    response.put("status", util.cfg("SuccessStatusText", "*"))
    response.put("message", rejectVo.getProposalRejectDesc())
    Map<String, String> extra = new HashMap<String, String>()
    extra.put("Reason", rejectVo.getProposalRejectDesc())
    response.put("Notifications", notify.fire("PROPOSAL_REJECTED", notify.paramsOf(existing, extra), null, util.str(existing.get("AgentCode")), ""))
    return response

} catch (Exception ex) {
    return errorHandler.handle("UPProposalReject", ex)
}
