/**
 * Work queues for bank staff, read from the platform search index.
 * Request:  { "ChannelCode": "SOHAR", "Type": "PROPOSAL" | "CANCELLATION" | "MINE", "Status": "PENDING" | "ISSUED" | "REJECTED" | "ALL" (cancellations: PENDING | ISSUED),
 *             "ProductCode", "FromDate", "ToDate", "PageNo", "PageSize" }
 * PROPOSAL = the Proposal Checker's queue, CANCELLATION = the Cancellation Checker's queue (Maker may read it), MINE = the caller's own submissions (Maker).
 * Response: Type, Status, PageNo, PageSize, Total, Records[].
 */
UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    UPWorklist worklist = (UPWorklist) getCommonService("UPWorklist")
    validator.validate("UPWorklist", input)
    String type = util.str(input.get("Type"))
    if (type == "CANCELLATION") {
        access.require(Arrays.asList(util.cfg("RoleCancellationChecker", "*"), util.cfg("RoleMaker", "*")))
        return worklist.cancellationList(input)
    }
    if (type == "MINE") {
        Map<String, Object> caller = access.require(Arrays.asList(util.cfg("RoleMaker", "*")))
        return worklist.proposalList(input, util.str(caller.get("UserId")))
    }
    access.require(Arrays.asList(util.cfg("RoleProposalChecker", "*")))
    return worklist.proposalList(input, "")

} catch (Exception ex) {
    return errorHandler.handle("UPWorklistApi", ex)
}
