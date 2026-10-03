/**
 * Dashboard figures. Two sections so the page can load them in parallel:
 *   SUMMARY    counts of proposals (submitted / pending / issued / rejected, pending older than a day) and cancellations, per product.
 *   COMMISSION premium and commission of the issued policies of ONE product (ProductCode) in the window, by plan; cancelled policies are shown apart.
 * Request: { "ChannelCode", "Section", "ProductCode" (COMMISSION), "Scope": "ALL" | "MINE", "FromDate", "ToDate" }  (default window: the last 30 days, at most DashboardMaxDays).
 * A caller who is only a Maker always sees their own submissions (Scope MINE).
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
    validator.validate("UPDashboard", input)
    Map<String, Object> caller = access.requireAny()
    List<String> roles = (List<String>) caller.get("Roles")
    boolean onlyMaker = roles.size() == 1 && roles.get(0) == util.cfg("RoleMaker", "*")
    String mine = (onlyMaker || util.str(input.get("Scope")) == "MINE") ? util.str(caller.get("UserId")) : ""
    java.time.LocalDate to = util.parseDate(input.get("ToDate")) ?: java.time.LocalDate.now()
    java.time.LocalDate from = util.parseDate(input.get("FromDate")) ?: to.minusDays(30)
    long days = java.time.temporal.ChronoUnit.DAYS.between(from, to)
    if (days < 0 || days > Integer.parseInt(util.cfg("DashboardMaxDays", "*"))) {
        util.fail("The date window must be between 0 and ${util.cfg('DashboardMaxDays', '*')} days".toString())
    }
    input.put("FromDate", from.toString())
    input.put("ToDate", to.toString())
    Map<String, Object> out
    if (util.str(input.get("Section")) == "COMMISSION") {
        String product = util.str(input.get("ProductCode"))
        if (!product) {
            util.fail("ProductCode is required for the COMMISSION section")
        }
        out = worklist.commissionSection(input, product, mine)
    } else {
        out = worklist.summary(input, mine)
    }
    out.put("FromDate", from.toString())
    out.put("ToDate", to.toString())
    out.put("Scope", mine ? "MINE" : "ALL")
    return out

} catch (Exception ex) {
    return errorHandler.handle("UPDashboard", ex)
}
