/**
 * Create a proposal (application). The request uses the native policy JSON
 * (PolicyLobList / PolicyRiskList / PlanList / PolicyCoverageList / BeneficiaryList ...).
 * The plan premium is taken from product data; coverages are filled from the plan when not supplied.
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
    validator.validate("UPProposal", input)
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    UPNotify notify = (UPNotify) getCommonService("UPNotify")
    Map<String, Object> caller = access.require(Arrays.asList(util.cfg("RoleMaker", "*")))
    if (input.get("ProposalNo")) {
        util.fail("ProposalNo must not be supplied when creating a proposal. Use update-proposal.")
    }
    Map<String, Object> payload = products.prepareProposal(input)
    // the maker's platform user id is kept on the proposal (AgentCode, searchable) so the checker queue and "my submissions" can find it
    payload.put("AgentCode", caller.get("UserId"))

    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    Map<String, Object> response = (Map<String, Object>) proposalSdkClient.proposalApi()
            .newApplicationRequestBuilder()
            .requestBody(payload)
            .doRequest()
            .getBody()
    Map<String, Object> shaped = (Map<String, Object>) shaper.shapeResponse(response)
    shaped.put("Notifications", notify.fire("SUBMITTED", notify.paramsOf(shaped, null), null, util.str(caller.get("UserId")), ""))
    return shaped

} catch (Exception ex) {
    return errorHandler.handle("UPProposal", ex)
}
