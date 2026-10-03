/**
 * Share a quotation, proposal or policy with the customer by Email and / or SMS (InsureMO SNS; dry run until the tenant has an account, see NotifyMode).
 * Request: { "ChannelCode", "DocType": "QUOTATION" | "PROPOSAL" | "POLICY", "Channel": "EMAIL" | "SMS" | "BOTH", "Email", "Mobile",
 *            "ProposalNo" | "PolicyNo" (PROPOSAL / POLICY), "Details": { InsuredName, ProductName, PlanName, Premium, EffectiveDate } (QUOTATION) }
 * Without Email / Mobile the customer details stored on the proposal / policy are used.
 * Response: DocType, Channel, Notifications[] ({Event, Recipient, Channel, To (masked), Status}).
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
    UPNotify notify = (UPNotify) getCommonService("UPNotify")
    UPWorklist worklist = (UPWorklist) getCommonService("UPWorklist")
    validator.validate("UPShare", input)
    access.requireAny()
    String docType = util.str(input.get("DocType"))
    String channel = util.str(input.get("Channel"))
    Map<String, Object> customer = new HashMap<String, Object>()
    customer.put("Email", util.str(input.get("Email")))
    customer.put("Mobile", util.str(input.get("Mobile")))
    Map<String, String> params
    String event
    if (docType == "QUOTATION") {
        event = util.cfg("ShareDocQuotation", "*")
        Map<String, Object> details = (Map<String, Object>) input.get("Details")
        if (details == null) {
            util.fail("Details is required to share a quotation")
        }
        params = new HashMap<String, String>()
        params.put("Insured", util.str(details.get("InsuredName")))
        params.put("Product", util.str(details.get("ProductName")))
        params.put("Plan", util.str(details.get("PlanName")))
        params.put("Premium", util.fmtMoney(details.get("Premium")))
        params.put("EffectiveDate", util.fmtDate(details.get("EffectiveDate")))
        params.put("Insurer", util.str(((UPProductData) getCommonService("UPProductData")).carrierOf(util.str(input.get("ProductCode")), util.str(input.get("ProductSubcode"))).get("CarrierName")))
    } else {
        String no = util.str(input.get(docType == "POLICY" ? "PolicyNo" : "ProposalNo"))
        if (!no) {
            util.fail((docType == "POLICY" ? "PolicyNo" : "ProposalNo") + " is required")
        }
        Map<String, Object> stored = docType == "POLICY" ? worklist.loadPolicy("", no) : worklist.loadPolicy(no, "")
        if (stored == null) {
            return errorHandler.notFound("UPShare", "No ${docType == 'POLICY' ? 'policy' : 'proposal'} found for ${no}".toString())
        }
        validator.requireChannel(stored, util.str(input.get("ChannelCode")))
        event = util.cfg(docType == "POLICY" ? "ShareDocPolicy" : "ShareDocProposal", "*")
        params = notify.paramsOf(stored, null)
        Map<String, Object> onFile = notify.customerOf(stored)
        if (!customer.get("Email")) {
            customer.put("Email", onFile.get("Email"))
        }
        if (!customer.get("Mobile")) {
            customer.put("Mobile", onFile.get("Mobile"))
        }
    }
    List<Map<String, Object>> sent = notify.fire(event, params, customer, "", channel == "BOTH" ? "" : channel)
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("DocType", docType)
    out.put("Channel", channel)
    out.put("Notifications", sent)
    return out

} catch (Exception ex) {
    return errorHandler.handle("UPShare", ex)
}
