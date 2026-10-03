/**
 * Cancellation - Checker. Creates the pending cancellation request for an issued policy and shows what an approval would do.
 * Request:  { "ChannelCode": "SOHAR", "PolicyNo" | "ProposalNo": "...", "CancellationDate": "2026-10-20", "CancelReason": "..." }
 * Response: RequestNo, RequestStatus, PolicyInfo, PolicyStatus (current), PremiumDetails, RefundDetails.
 * Repeating the call for a policy that already has a pending request returns that request (RequestExists = TrueValue).
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPCancelCheck", input)
    ((UPAccess) getCommonService("UPAccess")).require(Arrays.asList(util.cfg("RoleMaker", "*")))
    UPCancelService cancellation = (UPCancelService) getCommonService("UPCancelService")
    return cancellation.check(input)

} catch (Exception ex) {
    return errorHandler.handle("UPCancelCheck", ex)
}
