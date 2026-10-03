/**
 * UPDocBuilder - print data for the application form / certificate, document wording, commission view.
 */
import java.math.BigDecimal
import java.util.ArrayList
import java.util.HashMap
import java.util.List
import java.util.Map

String describe(String tableName, Object id) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    String key = util.str(id)
    if (!key) {
        return ""
    }
    for (Map<String, Object> row : util.getRecords(tableName)) {
        if (util.str(row.get("Id")) == key) {
            return util.str(row.get("Description"))
        }
    }
    return key
}

/** Benefit limit wording from UP_DocWording (ModeCode = BASIS:<LimitBasis>, falling back to the BASIS:Default row of the same table). */
String benefitText(Map<String, Object> benefit) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    String limit = util.fmtNumber(util.str(benefit.get("BenefitLimit")))
    String basis = util.str(benefit.get("LimitBasis"))
    String days = util.str(benefit.get("MaxDays"))
    List<Map<String, Object>> rows = util.filterRecords("UP_DocWording", ["ModeCode": "BASIS:" + basis])
    if (rows.isEmpty()) {
        rows = util.filterRecords("UP_DocWording", ["ModeCode": "BASIS:Default"])
    }
    if (rows.isEmpty()) {
        throw new IllegalStateException("Configuration missing in UP_DocWording for limit basis " + basis)
    }
    Map<String, String> values = new HashMap<String, String>()
    values.put("limit", limit)
    values.put("days", days)
    String text = ""
    for (Map<String, Object> row : rows) {
        if (util.str(row.get("Key")) == "Text") {
            text = text + util.fill(util.str(row.get("Value")), values)
        } else if (util.str(row.get("Key")) == "DaysText" && days) {
            text = text + util.fill(util.str(row.get("Value")), values)
        }
    }
    return text
}

/** Official English / Arabic benefit names (UP_BenefitText): [english, arabic]. A row is required for every benefit that is printed. */
List<String> docBenefit(String productCode, String code) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    for (Map<String, Object> row : util.filterRecords("UP_BenefitText", ["ProductCode": productCode, "BenefitCode": code])) {
        return [util.str(row.get("NameEn")), util.str(row.get("NameAr"))]
    }
    throw new IllegalStateException("Configuration missing in UP_BenefitText for " + productCode + " / " + code)
}

/** English / Arabic wording of the premium frequency, premium text and period of cover for a premium mode (UP_DocWording). */
Map<String, Object> premiumWording(String modeCode, String term, String premium) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> w = new LinkedHashMap<String, Object>()
    for (Map<String, Object> row : util.filterRecords("UP_DocWording", ["ModeCode": modeCode])) {
        w.put(util.str(row.get("Key")), util.str(row.get("Value")).replace("{premium}", premium).replace("{term}", term))
    }
    if (w.isEmpty()) {
        throw new IllegalStateException("Configuration missing in UP_DocWording for premium mode " + modeCode)
    }
    return w
}

Map<String, Object> buildPrintData(Map<String, Object> policy, String docType) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    String productCode = util.str(policy.get("ProductCode"))
    String subcode = util.str(policy.get("ProductSubcode"))
    Map<String, Object> variant = products.getVariant(productCode, subcode)
    Map<String, Object> data = new LinkedHashMap<String, Object>()
    data.put("DocType", docType)
    data.put("ProductCode", productCode)
    data.put("ProductName", util.str(variant.get("Description")))
    data.put("ApplicationNo", util.str(policy.get("ApplicationNo")))
    data.put("ProposalNo", util.str(policy.get("ProposalNo")))
    data.put("PolicyNo", util.str(policy.get("PolicyNo")))
    data.put("ApplicationDate", util.fmtDate(policy.get("ApplyDate")))
    data.put("IssueDate", util.fmtDate(policy.get("IssueDate")))
    data.put("CommencementDate", util.fmtDate(policy.get("EffectiveDate")))
    data.put("ExpiryDate", util.fmtDate(policy.get("ExpiryDate")))
    data.put("PolicyTerm", util.str(policy.get("PolicyTerm")))
    data.put("PremiumMode", util.str(policy.get("PremiumModeCode_CodeDesc")))
    data.put("Salutation", util.str(risk.get("Salutation_CodeDesc")))
    data.put("InsuredName", util.str(risk.get("InsuredName")))
    data.put("Gender", util.str(risk.get("Gender_CodeDesc")))
    data.put("DateOfBirth", util.fmtDate(risk.get("DateOfBirth")))
    data.put("ResidentStatus", util.str(risk.get("ResidentStatus_CodeDesc")))
    data.put("MaritalStatus", describe("InsMaritalStatus", risk.get("MaritalStatus")))
    data.put("IdNo", util.str(risk.get("IdNo")))
    data.put("MonthlyIncome", util.str(risk.get("MonthSalaryIncome")))
    data.put("Address", util.str(risk.get("Address")))
    data.put("PoBox", util.str(risk.get("PostCode")))
    data.put("Email", util.str(risk.get("Email")))
    data.put("Mobile", util.str(risk.get("Mobile")))
    data.put("BranchCode", util.str(policy.get("BranchCode")))
    data.put("BranchName", util.str(policy.get("BranchCode_CodeDesc")))
    data.put("UserName", util.str(policy.get("UserName")))
    List<Map<String, Object>> payments = (List<Map<String, Object>>) policy.get("PolicyPaymentInfoList")
    Map<String, Object> pay = (payments != null && !payments.isEmpty()) ? payments.get(0) : new HashMap<String, Object>()
    data.put("DebitAccountNo", util.str(pay.get("DebitAccountNo")))
    data.put("DebitRefNo", util.str(pay.get("DebitRefNo")))
    data.put("PaymentDate", util.fmtDate(pay.get("TransactionDate")))
    data.put("Premium", util.fmtMoney(risk.get("DuePremium")))

    List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
    Map<String, Object> plan = (plans != null && !plans.isEmpty()) ? plans.get(0) : new HashMap<String, Object>()
    String planId = util.str(plan.get("PlanId") ?: policy.get("PlanId"))
    data.put("PlanName", util.str(plan.get("PlanName")) ?: describe("Plan", planId))
    Map<String, Map<String, Object>> benefits = new HashMap<String, Map<String, Object>>()
    for (Map<String, Object> b : products.getBenefitRows(productCode, subcode, planId)) {
        benefits.put(util.str(b.get("BenefitCode")), b)
    }
    List<Map<String, Object>> coverages = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> c : (List<Map<String, Object>>) (plan.get("PolicyCoverageList") ?: new ArrayList<Map<String, Object>>())) {
        String code = util.str(c.get("ProductElementCode"))
        Map<String, Object> row = new LinkedHashMap<String, Object>()
        row.put("Code", code)
        List<String> docNames = docBenefit(productCode, code)
        row.put("Description", docNames.get(0))
        row.put("DescriptionAr", docNames.get(1))
        Map<String, Object> benefit = benefits.get(code)
        row.put("SumInsured", benefit != null ? benefitText(benefit) : util.fmtMoney(c.get("SumInsured")))
        coverages.add(row)
    }
    data.put("Coverages", coverages)
    data.put("PlanId", planId)
    data.put("PlanLabel", util.cfg("PlanLabelPrefix", "*") + planId)
    data.put("PolicyHolderName", util.str(risk.get("InsuredName")))
    String modeCode = util.str(policy.get("PremiumModeCode"))
    data.put("PremiumModeCode", modeCode)
    if (!util.str(policy.get("PolicyTerm"))) {
        throw new IllegalStateException("Policy has no PolicyTerm stored")
    }
    data.putAll(premiumWording(modeCode, util.str(policy.get("PolicyTerm")), util.fmtMoney(risk.get("DuePremium"))))
    data.put("FirstSumInsured", coverages.isEmpty() ? "" : util.str(coverages.get(0).get("SumInsured")))
    List<Map<String, Object>> beneficiaries = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> b : (List<Map<String, Object>>) (risk.get("BeneficiaryList") ?: new ArrayList<Map<String, Object>>())) {
        Map<String, Object> row = new LinkedHashMap<String, Object>()
        row.put("Name", util.str(b.get("BeneficaryName")))
        row.put("Relationship", util.str(b.get("RelationshipCode_CodeDesc")))
        row.put("Share", util.str(b.get("Share")))
        beneficiaries.add(row)
    }
    data.put("Beneficiaries", beneficiaries)
    return data
}

String rate(Object commission, Object premium) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    BigDecimal prem = util.toDecimal(premium)
    if (prem.compareTo(BigDecimal.ZERO) == 0) {
        return ""
    }
    return util.toDecimal(commission).multiply(util.percentBase()).divide(prem, util.moneyScale(), util.roundingMode()).toPlainString() + "%"
}

/** Commission view of one loaded policy (commission is read from the stored policy, not from configuration). */
Map<String, Object> commissionOfPolicy(Map<String, Object> policy) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
    Map<String, Object> plan = (plans != null && !plans.isEmpty()) ? plans.get(0) : new HashMap<String, Object>()
    Object premium = risk.get("DuePremium")
    Object commission = risk.get("Commission") != null ? risk.get("Commission") : lob.get("Commission")
    Map<String, Object> row = new LinkedHashMap<String, Object>()
    row.put("PolicyNo", util.str(policy.get("PolicyNo")))
    row.put("ProposalNo", util.str(policy.get("ProposalNo")))
    row.put("ProductCode", util.str(policy.get("ProductCode")))
    row.put("ProductSubcode", util.str(policy.get("ProductSubcode")))
    ((UPProductData) getCommonService("UPProductData")).addCarrier(row, util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    row.put("PlanId", util.str(plan.get("PlanId") ?: policy.get("PlanId")))
    row.put("PlanName", util.str(plan.get("PlanName")))
    row.put("PolicyStatus", util.str(policy.get("PolicyStatus_CodeDesc")))
    row.put("CommencementDate", util.fmtDate(policy.get("EffectiveDate")))
    row.put("BranchCode", util.str(policy.get("BranchCode")))
    row.put("Premium", util.fmtMoney(premium))
    row.put("Commission", util.fmtMoney(commission))
    row.put("CommissionRate", rate(commission, premium))
    row.put("PremiumRaw", util.str(premium))
    row.put("CommissionRaw", util.str(commission))
    return row
}
