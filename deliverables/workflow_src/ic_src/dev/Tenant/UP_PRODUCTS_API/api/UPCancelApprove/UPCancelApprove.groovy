/**
 * Cancellation - Approver. Approves (cancels the policy) or rejects the pending request created by the Checker.
 * Request:  { "ChannelCode": "SOHAR", "PolicyNo" | "ProposalNo": "...", "RequestNo": "<from the Checker>", "Decision": "APPROVE" | "REJECT" }
 * Response: RequestNo, RequestStatus, PolicyInfo, PolicyStatus, RefundPremium.
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
    validator.validate("UPCancelApprove", input)
    ((UPAccess) getCommonService("UPAccess")).require(Arrays.asList(util.cfg("RoleCancellationChecker", "*")))
    UPCancelService cancellation = (UPCancelService) getCommonService("UPCancelService")
    return cancellation.decide(input)

} catch (Exception ex) {
    return errorHandler.handle("UPCancelApprove", ex)
}
