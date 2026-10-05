/**
 * Get plans for a product variant. Same shape as the PA001 flow: the request is the policy body
 * (ProductCode + ProductSubcode, insured details), the response is that policy with every plan of the
 * variant in PolicyRiskList[].PlanList (PlanId, PlanName, DuePremium, Commission, PolicyCoverageList).
 * Optional: PremiumModeCode, PolicyTerm. Age and term rules are checked when the date of birth is supplied.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.quotation.QuotationSdkClient

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
    validator.validate("UPGetPlans", input)
    ((UPAccess) getCommonService("UPAccess")).requireAny()

    String productCode = util.str(input.get("ProductCode"))
    String subcode = util.str(input.get("ProductSubcode"))
    String modeCode = util.str(input.get("PremiumModeCode"))
    products.getVariant(productCode, subcode)
    Map<String, Object> rule = products.getRule(productCode, subcode)

    // Same gate as the PA001 Get Plans: the platform's own quotation validation (data dictionary and configured rules) runs first; the result is not used,
    // a rejection stops the request. Switched by UP_ApiConfig GetPlansPlatformValidate (TrueValue = on).
    if (util.isYes(util.cfg("GetPlansPlatformValidate", "*"))) {
        QuotationSdkClient quotationSdkClient = (QuotationSdkClient) getSDK("com.insuremo.sdk.services.quotation.QuotationSdkClient")
        Map<String, Object> platformCopy = (Map<String, Object>) IComposerJsonUtils.fromJSON(IComposerJsonUtils.toJSON(input), Map.class)
        quotationSdkClient.quotationApi().newValidateRequestBuilder().eventCode("").langId("").requestBody(platformCopy).doRequest()
    }

    List<Map<String, Object>> lobs = (List<Map<String, Object>>) input.get("PolicyLobList")
    if (lobs == null || lobs.isEmpty()) {
        lobs = new ArrayList<Map<String, Object>>()
        lobs.add(new LinkedHashMap<String, Object>())
        input.put("PolicyLobList", lobs)
    }
    Map<String, Object> lob = lobs.get(0)
    List<Map<String, Object>> risks = (List<Map<String, Object>>) lob.get("PolicyRiskList")
    if (risks == null || risks.isEmpty()) {
        risks = new ArrayList<Map<String, Object>>()
        risks.add(new LinkedHashMap<String, Object>())
        lob.put("PolicyRiskList", risks)
    }
    Map<String, Object> risk = risks.get(0)
    Map<String, String> config = util.configMap(productCode)
    int statusEffective = Integer.parseInt(util.cfgValue(config, "PolicyStatusEffective"))
    int sequenceStart = Integer.parseInt(util.cfgValue(config, "SequenceNumberStart"))

    boolean withCommission = shaper.returnCommission()
    List<Map<String, Object>> planList = new ArrayList<Map<String, Object>>()
    int seq = sequenceStart
    for (Map<String, Object> row : products.getPlanRows(productCode, subcode, modeCode)) {
        Map<String, Object> plan = new LinkedHashMap<String, Object>()
        plan.put("PlanId", util.str(row.get("IMOPlanCode")))
        plan.put("PlanName", util.str(row.get("IMOPlanName")))
        plan.put("DuePremium", util.toDecimal(row.get("Premium")))
        if (withCommission) {
            plan.put("Commission", util.toDecimal(row.get("Commission")))
        }
        List<Map<String, Object>> coverages = new ArrayList<Map<String, Object>>()
        for (Map<String, Object> b : products.getBenefitRows(productCode, subcode, util.str(row.get("IMOPlanCode")))) {
            Map<String, Object> cover = new LinkedHashMap<String, Object>()
            cover.put("CoverageCode", util.str(b.get("BenefitCode")))
            cover.put("CoverageDescription", util.str(b.get("BenefitDesc")))
            cover.put("IsAutoAttachedForm", util.cfgValue(config, "IsAutoAttachedForm"))
            cover.put("PolicyStatus", statusEffective)
            cover.put("ProductElementCode", util.str(b.get("BenefitCode")))
            cover.put("SequenceNumber", sequenceStart)
            cover.put("SumInsured", util.toDecimal(b.get("BenefitLimit")))
            coverages.add(cover)
        }
        plan.put("PolicyCoverageList", coverages)
        plan.put("PolicyStatus", statusEffective)
        plan.put("SequenceNumber", seq++)
        planList.add(plan)
    }
    risk.put("PlanList", planList)
    risk.putIfAbsent("ProductElementCode", util.cfgValue(config, "RiskElementCode"))
    lob.putIfAbsent("ProductCode", productCode)
    input.putIfAbsent("PolicyStatus", statusEffective)
    BigDecimal zero = new BigDecimal(util.cfgValue(config, "ZeroPremiumValue"))
    for (String key : ["DuePremium"] + util.cfgValue(config, "ZeroPremiumFields").split(",").toList()) {
        input.putIfAbsent(key, zero)
        lob.putIfAbsent(key, zero)
        risk.putIfAbsent(key, zero)
    }
    input.putIfAbsent("IsPremiumCalcSuccess", util.cfgValue(config, "IsPremiumCalcSuccess"))
    input.putIfAbsent("BusinessCateCode", util.cfgValue(config, "BusinessCateCode"))
    risk.putIfAbsent("PolicyStatus", statusEffective)
    List<Map<String, Object>> customers = (List<Map<String, Object>>) input.get("PolicyCustomerList")
    if (customers != null) {
        int customerSeq = sequenceStart
        for (Map<String, Object> customer : customers) {
            customer.putIfAbsent("IsInsured", util.cfgValue(config, "CustomerFlagNo"))
            customer.putIfAbsent("IsOrgParty", util.cfgValue(config, "CustomerFlagNo"))
            customer.putIfAbsent("IsPolicyHolder", util.cfgValue(config, "CustomerFlagNo"))
            customer.putIfAbsent("PolicyStatus", statusEffective)
            customer.putIfAbsent("SequenceNumber", customerSeq++)
        }
    }
    products.addCarrier(input, productCode, subcode)
    return input

} catch (Exception ex) {
    return errorHandler.handle("UPGetPlans", ex)
}
