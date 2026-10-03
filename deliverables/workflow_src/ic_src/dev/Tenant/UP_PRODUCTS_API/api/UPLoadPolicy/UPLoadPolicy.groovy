/**
 * Load a policy (policyNo) or a proposal (proposalNo). Commission is removed from the response.
 */
import com.insuremo.sdk.services.proposal.ProposalSdkClient

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    Map<String, Object> params = (Map<String, Object>) RequestParameter()
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPShaper shaper = (UPShaper) getCommonService("UPShaper")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPLoadPolicy", params)
    ((UPAccess) getCommonService("UPAccess")).requireAny()
    String policyNo = util.str(params.get("policyNo"))
    String proposalNo = util.str(params.get("proposalNo"))
    if (!policyNo && !proposalNo) {
        util.fail("policyNo or proposalNo is required")
    }
    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    Map<String, Object> response
    if (policyNo) {
        response = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                .policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
    } else {
        response = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                .proposalNo(proposalNo).withCodeDesc(util.yes()).doRequest().getBody()
    }
    if (response == null) {
        return errorHandler.notFound("UPLoadPolicy", "No ${policyNo ? 'policy' : 'proposal'} found for ${policyNo ?: proposalNo}".toString())
    }
    validator.requireChannel(response, util.str(params.get("ChannelCode")))
    return shaper.shapeResponse(response)

} catch (Exception ex) {
    return errorHandler.handle("UPLoadPolicy", ex)
}
