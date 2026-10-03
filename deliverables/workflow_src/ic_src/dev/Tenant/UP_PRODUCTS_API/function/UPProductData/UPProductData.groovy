/**
 * UPProductData - product master data (variants, rules, plans, benefits) and preparation of the proposal payload.
 */
import java.util.ArrayList
import java.util.HashMap
import java.util.List
import java.util.Map

Map<String, Object> getVariant(String productCode, String subcode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (!productCode) {
        util.fail("ProductCode is required")
    }
    if (!subcode) {
        util.fail("ProductSubcode is required")
    }
    Map<String, Object> filters = new HashMap<String, Object>()
    filters.put("IMOProductCode", productCode)
    filters.put("CarrierProductCode", subcode)
    List<Map<String, Object>> rows = util.filterRecords("ProductMaster", filters)
    if (rows.isEmpty() || util.isNo(rows.get(0).get("IsActive"))) {
        util.fail("Unknown or inactive product / sub-product: ${productCode} / ${subcode}".toString())
    }
    return rows.get(0)
}

/**
 * Insurer (carrier) of a product variant: the code is on the product (UP_ProductMaster.CarrierCode), the name comes from UP_Carrier.
 * A product without a carrier, or a carrier that is missing or inactive in UP_Carrier, is a configuration error (UP-CONFIG), never a default.
 */
Map<String, Object> carrierOf(String productCode, String subcode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> variant = getVariant(productCode, subcode)
    String code = util.str(variant.get("CarrierCode"))
    for (Map<String, Object> row : util.getRecords("UP_Carrier")) {
        if (util.str(row.get("CarrierCode")) == code && !util.isNo(row.get("IsActive"))) {
            Map<String, Object> carrier = new LinkedHashMap<String, Object>()
            carrier.put("CarrierCode", code)
            carrier.put("CarrierName", util.str(row.get("CarrierName")))
            return carrier
        }
    }
    throw new IllegalStateException("Carrier " + code + " of product " + productCode + " is not defined or not active in UP_Carrier")
}

/** Adds CarrierCode and CarrierName (the insurer of the product) to a response map. */
void addCarrier(Map<String, Object> target, String productCode, String subcode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (!util.str(productCode) || !util.str(subcode)) {
        return
    }
    Map<String, Object> carrier = carrierOf(util.str(productCode), util.str(subcode))
    target.put("CarrierCode", carrier.get("CarrierCode"))
    target.put("CarrierName", carrier.get("CarrierName"))
}

Map<String, Object> getRule(String productCode, String subcode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> filters = new HashMap<String, Object>()
    filters.put("ProductCode", productCode)
    filters.put("ProductSubcode", subcode)
    List<Map<String, Object>> rows = util.filterRecords("ProductRule", filters)
    return rows.isEmpty() ? new HashMap<String, Object>() : rows.get(0)
}

List<String> allowedModes(Map<String, Object> rule) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<String> modes = new ArrayList<String>()
    for (String m : util.str(rule.get("PremiumModes")).split(",")) {
        if (m.trim()) {
            modes.add(m.trim())
        }
    }
    return modes
}

/** Plan rows (premium + commission) for the variant and premium mode. */
List<Map<String, Object>> getPlanRows(String productCode, String subcode, String premiumModeCode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> filters = new HashMap<String, Object>()
    filters.put("IMOProductCode", productCode)
    filters.put("CarrierProductCode", subcode)
    List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> row : util.filterRecords("ProductPlanRelation", filters)) {
        if (util.isNo(row.get("IsActive"))) {
            continue
        }
        String rowMode = util.str(row.get("PremiumModeCode"))
        // rows without a mode apply to every allowed mode; rows with a mode apply to that mode only
        if (premiumModeCode && rowMode && rowMode != premiumModeCode) {
            continue
        }
        rows.add(row)
    }
    rows.sort { Map<String, Object> a, Map<String, Object> b -> util.str(a.get("IMOPlanCode")) <=> util.str(b.get("IMOPlanCode")) }
    return rows
}

List<Map<String, Object>> getBenefitRows(String productCode, String subcode, String planCode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> filters = new HashMap<String, Object>()
    filters.put("IMOProductCode", productCode)
    filters.put("CarrierProductCode", subcode)
    filters.put("IMOPlanCode", planCode)
    List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> row : util.filterRecords("UP_PlanBenefitRelation", filters)) {
        if (!util.isNo(row.get("IsApplicable"))) {
            rows.add(row)
        }
    }
    return rows
}

/** Plans for the front end: premium and benefits only, never commission. */
List<Map<String, Object>> buildPlanView(String productCode, String subcode, String premiumModeCode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<Map<String, Object>> plans = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> row : getPlanRows(productCode, subcode, premiumModeCode)) {
        Map<String, Object> plan = new HashMap<String, Object>()
        plan.put("PlanId", util.str(row.get("IMOPlanCode")))
        plan.put("PlanName", util.str(row.get("IMOPlanName")))
        plan.put("Premium", util.toDecimal(row.get("Premium")))
        plan.put("PremiumModeCode", util.str(row.get("PremiumModeCode")) ?: premiumModeCode)
        List<Map<String, Object>> benefits = new ArrayList<Map<String, Object>>()
        for (Map<String, Object> b : getBenefitRows(productCode, subcode, util.str(row.get("IMOPlanCode")))) {
            Map<String, Object> benefit = new HashMap<String, Object>()
            benefit.put("BenefitCode", util.str(b.get("BenefitCode")))
            benefit.put("BenefitDesc", util.str(b.get("BenefitDesc")))
            benefit.put("SumInsured", util.str(b.get("BenefitLimit")))
            benefit.put("LimitBasis", util.str(b.get("LimitBasis")))
            benefit.put("MaxDays", util.str(b.get("MaxDays")))
            benefits.add(benefit)
        }
        plan.put("Benefits", benefits)
        plans.add(plan)
    }
    return plans
}

/**
 * Validates the request against product data and fills the authoritative values (plan premium, commission,
 * coverages when none are supplied). Returns the payload ready for the native proposal SDK.
 */
Map<String, Object> prepareProposal(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPShaper shaper = (UPShaper) getCommonService("UPShaper")
    String productCode = util.str(input.get("ProductCode"))
    String subcode = util.str(input.get("ProductSubcode"))
    Map<String, Object> variant = getVariant(productCode, subcode)
    Map<String, Object> rule = getRule(productCode, subcode)
    String modeCode = util.str(input.get("PremiumModeCode"))
    String term = util.str(input.get("PolicyTerm"))
    String planId = util.str(input.get("PlanId"))

    List<Map<String, Object>> lobs = (List<Map<String, Object>>) input.get("PolicyLobList")
    if (lobs == null || lobs.isEmpty()) {
        util.fail("PolicyLobList is required")
    }
    Map<String, Object> lob = lobs.get(0)
    List<Map<String, Object>> risks = (List<Map<String, Object>>) lob.get("PolicyRiskList")
    if (risks == null || risks.isEmpty()) {
        util.fail("PolicyRiskList is required")
    }
    Map<String, Object> risk = risks.get(0)
    List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
    if (!planId) {
        util.fail("PlanId is required")
    }
    // The product premium calculation (<CODE>_PREM_CALC) builds the plan, its coverages, premium and commission
    // from the product tables, so any client supplied PlanList is dropped to avoid a duplicate plan row.
    risk.remove("PlanList")
    if (!risk.get("ProductElementCode")) {
        risk.put("ProductElementCode", util.cfg("RiskElementCode", productCode))
    }
    lob.put("ProductCode", productCode)
    input.put("PlanId", planId)
    input.put("ProductSubcode", subcode)
    input.remove("DuePremium")
    // server-owned fields are never taken from the caller; the branch must be one the platform accepts (needed to cancel the policy later)
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    security.stripServerOwned(input)
    security.defaultOrgCode(input)
    // Payment details are stored as plain policy fields. The platform installment rating would otherwise
    // re-round the premium, so PolicyPaymentInfoList is flattened here and rebuilt by shaper.shapeResponse().
    List<Map<String, Object>> payments = (List<Map<String, Object>>) input.get("PolicyPaymentInfoList")
    if (payments != null && !payments.isEmpty()) {
        Map<String, Object> payment = payments.get(0)
        input.put("PaymentLGCode", util.str(payment.get("LGCode")))
        input.put("PaymentLCCode", util.str(payment.get("LCCode")))
        input.put("PaymentDebitAccountNo", util.str(payment.get("DebitAccountNo")))
        input.put("PaymentDebitRefNo", util.str(payment.get("DebitRefNo")))
        if (payment.get("IsInstallment") != null) {
            input.put("PaymentIsInstallment", util.str(payment.get("IsInstallment")))
        }
        if (payment.get("TransactionDate")) {
            input.put("PaymentTransactionDate", util.str(payment.get("TransactionDate")))
        }
    }
    input.remove("PolicyPaymentInfoList")
    return input
}

/** Display name of a product variant (UP_ProductMaster CarrierProductName); empty when unknown. */
String variantName(String productCode, String subcode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    for (Map<String, Object> row : util.getRecords("ProductMaster")) {
        if (util.str(row.get("IMOProductCode")) == productCode && util.str(row.get("CarrierProductCode")) == subcode) {
            return util.str(row.get("CarrierProductName"))
        }
    }
    return ""
}
