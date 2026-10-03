/**
 * Cancellation - details of a pending request for the Cancellation Checker (and the maker who raised it). Creates and changes nothing.
 * Request:  { "ChannelCode": "SOHAR", "PolicyNo" | "ProposalNo": "..." }
 * Response: RequestNo, RequestedBy, RequestedOn, CancelReason, CancellationDate, PolicyInfo, PremiumDetails, RefundDetails, CanDecide.
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
    validator.validate("UPCancelDetail", input)
    ((UPAccess) getCommonService("UPAccess")).require(Arrays.asList(util.cfg("RoleMaker", "*"), util.cfg("RoleCancellationChecker", "*")))
    if (!util.str(input.get("PolicyNo")) && !util.str(input.get("ProposalNo"))) {
        util.fail("PolicyNo or ProposalNo is required")
    }
    UPCancelService cancellation = (UPCancelService) getCommonService("UPCancelService")
    return cancellation.detail(input)

} catch (Exception ex) {
    return errorHandler.handle("UPCancelDetail", ex)
}
