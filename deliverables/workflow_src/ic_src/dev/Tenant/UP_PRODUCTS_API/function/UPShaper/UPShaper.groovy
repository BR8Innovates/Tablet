/**
 * UPShaper - shapes the responses returned to callers (commission, premium fields, payment info).
 */
import java.math.BigDecimal
import java.util.ArrayList
import java.util.Arrays
import java.util.List
import java.util.Map

/** Removes commission from a policy / proposal body before it is returned to a front-end caller. */
Object stripCommission(Object node) {
    if (node instanceof Map) {
        Map<String, Object> map = (Map<String, Object>) node
        map.remove("Commission")
        for (Object value : new ArrayList<Object>(map.values())) {
            stripCommission(value)
        }
    } else if (node instanceof List) {
        for (Object item : (List<Object>) node) {
            stripCommission(item)
        }
    }
    return node
}

/** Rebuilds PolicyPaymentInfoList from the flattened payment fields. */
Object restorePayment(Object body) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (!(body instanceof Map)) {
        return body
    }
    Map<String, Object> map = (Map<String, Object>) body
    if (map.get("PaymentLGCode") != null || map.get("PaymentLCCode") != null || map.get("PaymentDebitRefNo") != null
            || map.get("PaymentDebitAccountNo") != null) {
        Map<String, Object> payment = new LinkedHashMap<String, Object>()
        payment.put("LGCode", map.get("PaymentLGCode"))
        payment.put("LCCode", map.get("PaymentLCCode"))
        payment.put("IsInstallment", map.get("PaymentIsInstallment"))
        payment.put("DebitAccountNo", map.get("PaymentDebitAccountNo"))
        payment.put("DebitRefNo", map.get("PaymentDebitRefNo"))
        payment.put("TransactionDate", map.get("PaymentTransactionDate"))
        if (util.isNo(payment.get("IsInstallment"))) {
            // single payment: same instalment structure as the PA001 flow; every value comes from UP_ApiConfig
            Map<String, String> config = util.configMap(util.str(map.get("ProductCode")))
            payment.put("InstallmentPeriodCount", Integer.parseInt(util.cfgValue(config, "InstalmentPeriodCount")))
            payment.put("PayRate", Integer.parseInt(util.cfgValue(config, "InstalmentPayRate")))
            Map<String, Object> instalment = new LinkedHashMap<String, Object>()
            instalment.put("FeeSeq", Integer.parseInt(util.cfgValue(config, "InstalmentFeeSeq")))
            instalment.put("InstallmentAmount", new BigDecimal(util.cfgValue(config, "InstalmentAmount")))
            instalment.put("InstallmentAmountLocal", new BigDecimal(util.cfgValue(config, "InstalmentAmount")))
            instalment.put("InstallmentDate", util.str(map.get("EffectiveDate")).take(10))
            instalment.put("InstallmentPeriodSeq", Integer.parseInt(util.cfgValue(config, "InstalmentPeriodSeq")))
            instalment.put("PolicyStatus", Integer.parseInt(util.cfgValue(config, "PolicyStatusEffective")))
            instalment.put("SequenceNumber", Integer.parseInt(util.cfgValue(config, "SequenceNumberStart")))
            List<Map<String, Object>> instalments = new ArrayList<Map<String, Object>>()
            instalments.add(instalment)
            payment.put("InstallmentList", instalments)
            payment.put("PolicyStatus", Integer.parseInt(util.cfgValue(config, "PolicyStatusEffective")))
            payment.put("SequenceNumber", Integer.parseInt(util.cfgValue(config, "SequenceNumberStart")))
        }
        List<Map<String, Object>> payments = new ArrayList<Map<String, Object>>()
        payments.add(payment)
        map.put("PolicyPaymentInfoList", payments)
    }
    for (String key : ["PaymentLGCode", "PaymentLCCode", "PaymentDebitAccountNo", "PaymentDebitRefNo", "PaymentIsInstallment", "PaymentTransactionDate"]) {
        map.remove(key)
    }
    return map
}

/** Commission is returned only while UP_ApiConfig ReturnCommission equals the TrueValue. */
boolean returnCommission() {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    return util.isYes(util.cfg("ReturnCommission", "*"))
}

/** Adds the premium structure fields the PA001 responses carry (zero where the level is not rated) and the plan row premium / commission. */
void enrichPremiumFields(Map<String, Object> map) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, String> config = util.configMap(util.str(map.get("ProductCode")))
    List<String> zeroFields = Arrays.asList(util.cfgValue(config, "ZeroPremiumFields").split(","))
    BigDecimal zero = new BigDecimal(util.cfgValue(config, "ZeroPremiumValue"))
    map.putIfAbsent("AnnualPremium", zero)
    List<Map<String, Object>> lobs = (List<Map<String, Object>>) map.get("PolicyLobList")
    if (lobs == null) {
        return
    }
    for (Map<String, Object> lob : lobs) {
        lob.putIfAbsent("StandardGrossPremium", zero)
        List<Map<String, Object>> risks = (List<Map<String, Object>>) lob.get("PolicyRiskList")
        if (risks == null) {
            continue
        }
        for (Map<String, Object> risk : risks) {
            for (String key : zeroFields) {
                risk.putIfAbsent(key, zero)
            }
            List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
            if (plans != null) {
                for (Map<String, Object> plan : plans) {
                    if (plan.get("DuePremium") == null && risk.get("DuePremium") != null) {
                        plan.put("DuePremium", risk.get("DuePremium"))
                    }
                    if (plan.get("Commission") == null && risk.get("Commission") != null) {
                        plan.put("Commission", risk.get("Commission"))
                    }
                }
            }
        }
    }
}

/** Response shaping for every front-end facing API: same structure as the PA001 flow, payment info in its original shape. */
Object shapeResponse(Object body) {
    if (!returnCommission()) {
        stripCommission(body)
    }
    if (body instanceof Map) {
        enrichPremiumFields((Map<String, Object>) body)
        UPProductData products = (UPProductData) getCommonService("UPProductData")
        Map<String, Object> map = (Map<String, Object>) body
        products.addCarrier(map, String.valueOf(map.get("ProductCode") == null ? "" : map.get("ProductCode")), String.valueOf(map.get("ProductSubcode") == null ? "" : map.get("ProductSubcode")))
    }
    return restorePayment(body)
}
