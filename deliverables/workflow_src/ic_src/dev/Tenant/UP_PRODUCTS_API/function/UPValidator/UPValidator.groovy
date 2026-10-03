/**
 * UPValidator - request validation: field rules (UP_FieldRule), cross-field and product rules, state / channel checks.
 */
import java.math.BigDecimal
import java.time.LocalDate
import java.time.temporal.ChronoUnit
import java.util.ArrayList
import java.util.List
import java.util.Map

/** A proposal can only be updated / issued / rejected while it is open (status codes come from UP_ApiConfig). */
void requireOpenProposal(Map<String, Object> stored, String action) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, String> config = util.configMap(util.str(stored.get("ProductCode")))
    String status = util.str(stored.get("ProposalStatus"))
    if (status == util.cfgValue(config, "ProposalStatusIssued")) {
        throw new IllegalArgumentException("CONFLICT:The proposal has already been issued (policy ${util.str(stored.get('PolicyNo'))}); it cannot be ${action}".toString())
    }
    if (status == util.cfgValue(config, "ProposalStatusRejected")) {
        throw new IllegalArgumentException("CONFLICT:The proposal has been rejected; it cannot be ${action}".toString())
    }
}

/** The stored proposal / policy must belong to the product the caller names. */
void requireProductMatch(Map<String, Object> stored, String productCode, String subcode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<Map<String, Object>> errors = new ArrayList<Map<String, Object>>()
    if (productCode && util.str(stored.get("ProductCode")) != productCode) {
        errors.add(util.fieldError("ProductCode", "MISMATCH", "The proposal belongs to product ${util.str(stored.get('ProductCode'))}, not ${productCode}".toString()))
    }
    if (subcode && util.str(stored.get("ProductSubcode")) != subcode) {
        errors.add(util.fieldError("ProductSubcode", "MISMATCH", "The proposal belongs to sub-product ${util.str(stored.get('ProductSubcode'))}, not ${subcode}".toString()))
    }
    util.throwValidation(errors)
}

/** The stored proposal / policy must have been created by the channel that calls (ChannelCode is saved on every proposal). */
void requireChannel(Map<String, Object> stored, String channelCode) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (util.str(stored.get("ChannelCode")) != channelCode) {
        throw new IllegalArgumentException("CONFLICT:The record does not belong to channel ${channelCode}".toString())
    }
}

boolean codeExists(String table, String column, String value) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    for (Map<String, Object> row : util.getRecords(table)) {
        if (util.str(row.get(column)) == value && !util.isNo(row.get("IsActive"))) {
            return true
        }
    }
    return false
}

/**
 * Field level validation. Rules come from UP_FieldRule (per API) and product rules from UP_ProductRule.
 * All problems are collected and returned together as HTTP 400 with errors[].
 */
void validate(String api, Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<Map<String, Object>> errors = new ArrayList<Map<String, Object>>()
    String productCode = util.str(input.get("ProductCode"))
    Map<String, String> config = util.configMap("*")
    int patternMaxLength = Integer.parseInt(util.cfgValue(config, "PatternMaxLength"))
    int patternMaxInput = Integer.parseInt(util.cfgValue(config, "PatternMaxInput"))
    for (Map<String, Object> rule : util.filterRecords("UP_FieldRule", ["Api": api])) {
        String applies = util.str(rule.get("AppliesTo"))
        if (applies != "*" && !applies.split(",").contains(productCode)) {
            continue
        }
        if (util.str(rule.get("WhenPath")) && util.str(util.pathValue(input, util.str(rule.get("WhenPath")))) != util.str(rule.get("WhenValue"))) {
            continue
        }
        String path = util.str(rule.get("Path"))
        String label = util.str(rule.get("Label")) ?: path
        Object raw = util.pathValue(input, path)
        if (raw instanceof Map || raw instanceof List) {
            errors.add(util.fieldError(path, "INVALID_TYPE", "${label} must be a single value".toString()))
            continue
        }
        String value = raw == null ? "" : util.str(raw)
        if (value.isEmpty()) {
            if (util.isYes(rule.get("Required"))) {
                errors.add(util.fieldError(path, "REQUIRED", "${label} is required".toString()))
            }
            continue
        }
        String type = util.str(rule.get("DataType"))
        if (type == "string" || type == "enum") {
            if (util.str(rule.get("MinLength")) && value.length() < Integer.parseInt(util.str(rule.get("MinLength")))) {
                errors.add(util.fieldError(path, "TOO_SHORT", "${label} must be at least ${rule.get('MinLength')} characters".toString()))
                continue
            }
            if (util.str(rule.get("MaxLength")) && value.length() > Integer.parseInt(util.str(rule.get("MaxLength")))) {
                errors.add(util.fieldError(path, "TOO_LONG", "${label} must be at most ${rule.get('MaxLength')} characters".toString()))
                continue
            }
        }
        if (type == "enum" && !util.str(rule.get("EnumValues")).split(",").contains(value)) {
            errors.add(util.fieldError(path, "NOT_ALLOWED", "${label} must be one of ${rule.get('EnumValues')}".toString()))
            continue
        }
        String pattern = util.str(rule.get("Pattern"))
        if (pattern) {
            // patterns come from a table: bound their size and the input size so a bad pattern cannot tie up a request
            if (pattern.length() > patternMaxLength || value.length() > patternMaxInput || !java.util.regex.Pattern.compile(pattern).matcher(value).matches()) {
                errors.add(util.fieldError(path, "INVALID_FORMAT", "${label} has an invalid format".toString()))
                continue
            }
        }
        if (type == "integer" || type == "decimal") {
            BigDecimal number
            try {
                number = new BigDecimal(value)
            } catch (Exception e) {
                errors.add(util.fieldError(path, "INVALID_TYPE", "${label} must be a number".toString()))
                continue
            }
            if (type == "integer" && number.stripTrailingZeros().scale() > 0) {
                errors.add(util.fieldError(path, "INVALID_TYPE", "${label} must be a whole number".toString()))
                continue
            }
            if (util.str(rule.get("MinValue")) && number < new BigDecimal(util.str(rule.get("MinValue")))) {
                errors.add(util.fieldError(path, "OUT_OF_RANGE", "${label} must be at least ${rule.get('MinValue')}".toString()))
                continue
            }
            if (util.str(rule.get("MaxValue")) && number > new BigDecimal(util.str(rule.get("MaxValue")))) {
                errors.add(util.fieldError(path, "OUT_OF_RANGE", "${label} must be at most ${rule.get('MaxValue')}".toString()))
                continue
            }
        }
        if (type == "date") {
            try {
                LocalDate.parse(value.substring(0, 10))
            } catch (Exception e) {
                errors.add(util.fieldError(path, "INVALID_FORMAT", "${label} is not a valid date (yyyy-MM-dd)".toString()))
                continue
            }
        }
        if (util.str(rule.get("CodeTable"))) {
            String table = util.str(rule.get("CodeTable"))
            String column = util.str(rule.get("CodeColumn"))
            if (!codeExists(table, column, value)) {
                errors.add(util.fieldError(path, "UNKNOWN_VALUE", "${label} '${value}' is not a valid ${table} value".toString()))
            }
        }
    }
    boolean productFieldBad = false
    for (Map<String, Object> e : errors) {
        if (util.str(e.get("field")) == "ProductCode" || util.str(e.get("field")) == "ProductSubcode") {
            productFieldBad = true
        }
    }
    errors.addAll(crossFieldErrors(api, input, productFieldBad))
    util.throwValidation(errors)
}

/** Rules that need several fields or product data. Only runs on values that already passed the field rules. */
List<Map<String, Object>> crossFieldErrors(String api, Map<String, Object> input, boolean productFieldBad) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    List<Map<String, Object>> errors = new ArrayList<Map<String, Object>>()
    Map<String, String> config = util.configMap("*")
    String risk = "PolicyLobList[0].PolicyRiskList[0]"
    if (api == "UPProposal" || api == "UPUpdateProposal" || api == "UPGetPlans") {
        String productCode = util.str(input.get("ProductCode"))
        String subcode = util.str(input.get("ProductSubcode"))
        if (productFieldBad) {
            // product / sub-product format errors are already reported
        } else if (productCode && util.filterRecords("ProductMaster", ["IMOProductCode": productCode]).isEmpty()) {
            errors.add(util.fieldError("ProductCode", "UNKNOWN_VALUE", "Unknown product ${productCode}".toString()))
        } else if (productCode && subcode && util.filterRecords("ProductMaster", ["IMOProductCode": productCode, "CarrierProductCode": subcode]).isEmpty()) {
            errors.add(util.fieldError("ProductSubcode", "UNKNOWN_VALUE", "Unknown sub-product ${subcode} for ${productCode}".toString()))
        } else if (productCode && subcode) {
            // CarrierCode is optional; when sent it must be the insurer of the product
            String carrierCode = util.str(input.get("CarrierCode"))
            if (carrierCode && carrierCode != util.str(products.carrierOf(productCode, subcode).get("CarrierCode"))) {
                errors.add(util.fieldError("CarrierCode", "MISMATCH", "Product ${productCode} / ${subcode} is not offered by carrier ${carrierCode}".toString()))
            }
            Map<String, Object> rule = products.getRule(productCode, subcode)
            String mode = util.str(input.get("PremiumModeCode"))
            String term = util.str(input.get("PolicyTerm"))
            String dob = util.str(util.pathValue(input, risk + ".DateOfBirth"))
            errors.addAll(entryErrors(rule, dob, util.str(input.get("EffectiveDate")), mode, term))
            if (!mode && api == "UPGetPlans") {
                for (Map<String, Object> row : products.getPlanRows(productCode, subcode, "")) {
                    if (util.str(row.get("PremiumModeCode"))) {
                        errors.add(util.fieldError("PremiumModeCode", "REQUIRED", "PremiumModeCode is required for this product (plans differ by premium mode)"))
                        break
                    }
                }
            }
            String planId = util.str(input.get("PlanId"))
            if (planId && mode) {
                boolean found = false
                for (Map<String, Object> row : products.getPlanRows(productCode, subcode, mode)) {
                    if (util.str(row.get("IMOPlanCode")) == planId) {
                        found = true
                    }
                }
                if (!found) {
                    errors.add(util.fieldError("PlanId", "NOT_ALLOWED", "Plan ${planId} is not available for ${productCode} / ${subcode} and premium mode ${mode}".toString()))
                }
            }
        }
        LocalDate effective = util.parseDate(input.get("EffectiveDate"))
        LocalDate expiry = util.parseDate(input.get("ExpiryDate"))
        if (effective != null && api != "UPGetPlans") {
            LocalDate earliest = LocalDate.now().plusDays(Long.parseLong(util.cfgValue(config, "EffectiveDateMinOffsetDays")))
            if (effective.isBefore(earliest)) {
                errors.add(util.fieldError("EffectiveDate", "OUT_OF_RANGE", "EffectiveDate cannot be before ${earliest}".toString()))
            }
        }
        if (effective != null && expiry != null && !expiry.isAfter(effective)) {
            errors.add(util.fieldError("ExpiryDate", "OUT_OF_RANGE", "ExpiryDate must be after EffectiveDate"))
        }
        LocalDate dobDate = util.parseDate(util.pathValue(input, risk + ".DateOfBirth"))
        if (dobDate != null && dobDate.isAfter(LocalDate.now())) {
            errors.add(util.fieldError(risk + ".DateOfBirth", "OUT_OF_RANGE", "DateOfBirth cannot be in the future"))
        }
        Object beneficiaries = util.pathValue(input, risk + ".BeneficiaryList")
        if (beneficiaries instanceof List && !((List<Object>) beneficiaries).isEmpty()) {
            BigDecimal total = BigDecimal.ZERO
            boolean numeric = true
            for (Object b : (List<Object>) beneficiaries) {
                try {
                    total = total + new BigDecimal(util.str(((Map<String, Object>) b).get("Share")))
                } catch (Exception e) {
                    numeric = false
                }
            }
            BigDecimal shareTotal = new BigDecimal(util.cfgValue(config, "BeneficiaryShareTotal"))
            if (numeric && total.compareTo(shareTotal) != 0) {
                errors.add(util.fieldError(risk + ".BeneficiaryList", "INVALID_TOTAL", "Beneficiary shares must total ${shareTotal} (got ${total})".toString()))
            }
        }
    }
    if (api == "UPLoadPolicy" && !util.str(input.get("policyNo")) && !util.str(input.get("proposalNo"))) {
        errors.add(util.fieldError("policyNo", "REQUIRED", "policyNo or proposalNo is required"))
    }
    if (api == "UPLoadPolicy" && util.str(input.get("policyNo")) && util.str(input.get("proposalNo"))) {
        errors.add(util.fieldError("proposalNo", "NOT_ALLOWED", "Send either policyNo or proposalNo, not both"))
    }
    if (api == "UPCancelCheck" || api == "UPCancelApprove") {
        if (!util.str(input.get("PolicyNo")) && !util.str(input.get("ProposalNo"))) {
            errors.add(util.fieldError("PolicyNo", "REQUIRED", "PolicyNo or ProposalNo is required"))
        }
        if (util.str(input.get("PolicyNo")) && util.str(input.get("ProposalNo"))) {
            errors.add(util.fieldError("ProposalNo", "NOT_ALLOWED", "Send either PolicyNo or ProposalNo, not both"))
        }
    }
    if (api == "UPListMasterTable") {
        String tableName = util.str(input.get("DataTableName"))
        if (tableName && !util.cfgValue(config, "MasterTables").split(",").contains(tableName)) {
            errors.add(util.fieldError("DataTableName", "NOT_ALLOWED", "DataTableName must be one of ${util.cfgValue(config, 'MasterTables')}".toString()))
        }
    }
    if (api == "UPFeedFile") {
        LocalDate from = util.parseDate(util.pathValue(input, "FromRangeConditions.EffectiveDate"))
        LocalDate to = util.parseDate(util.pathValue(input, "ToRangeConditions.EffectiveDate"))
        if (from != null && to != null && to.isBefore(from)) {
            errors.add(util.fieldError("ToRangeConditions.EffectiveDate", "OUT_OF_RANGE", "To date cannot be before the from date"))
        }
        String pc = util.str(util.pathValue(input, "Conditions.ProductCode"))
        if (pc && util.filterRecords("ProductMaster", ["IMOProductCode": pc]).isEmpty()) {
            errors.add(util.fieldError("Conditions.ProductCode", "UNKNOWN_VALUE", "Unknown product ${pc}".toString()))
        }
    }
    if (api == "UPCommissionQuery") {
        boolean byPolicy = util.str(input.get("PolicyNo")) != ""
        boolean byProduct = util.str(input.get("ProductCode")) != "" && util.str(input.get("FromDate")) == ""
        boolean byPeriod = util.str(input.get("FromDate")) != "" && util.str(input.get("ToDate")) != ""
        if (!byPolicy && !byProduct && !byPeriod) {
            errors.add(util.fieldError("PolicyNo", "REQUIRED", "Provide PolicyNo, or ProductCode (+ ProductSubcode / PlanId), or FromDate and ToDate"))
        }
        if ((util.str(input.get("FromDate")) != "") != (util.str(input.get("ToDate")) != "")) {
            errors.add(util.fieldError("ToDate", "REQUIRED", "FromDate and ToDate must be sent together"))
        }
        LocalDate from = util.parseDate(input.get("FromDate"))
        LocalDate to = util.parseDate(input.get("ToDate"))
        if (from != null && to != null && to.isBefore(from)) {
            errors.add(util.fieldError("ToDate", "OUT_OF_RANGE", "ToDate cannot be before FromDate"))
        }
        String pc = util.str(input.get("ProductCode"))
        if (pc && util.filterRecords("ProductMaster", ["IMOProductCode": pc]).isEmpty()) {
            errors.add(util.fieldError("ProductCode", "UNKNOWN_VALUE", "Unknown product ${pc}".toString()))
        }
    }
    return errors
}

/** Age, term and premium mode checks from UP_ProductRule, returned as field errors. */
List<Map<String, Object>> entryErrors(Map<String, Object> rule, String dateOfBirth, String effectiveDate, String premiumModeCode, String policyTerm) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    List<Map<String, Object>> errors = new ArrayList<Map<String, Object>>()
    String risk = "PolicyLobList[0].PolicyRiskList[0]"
    List<String> modes = products.allowedModes(rule)
    if (premiumModeCode && !modes.isEmpty() && !modes.contains(premiumModeCode)) {
        errors.add(util.fieldError("PremiumModeCode", "NOT_ALLOWED", "Premium mode ${premiumModeCode} is not allowed for this product. Allowed: ${modes.join(',')}".toString()))
    }
    if (policyTerm && policyTerm.matches("^[0-9]+\$") && premiumModeCode) {
        Map<String, String> config = util.configMap("*")
        String singleMode = util.cfgValue(config, "SinglePremiumModeCode")
        int fixedTerm = Integer.parseInt(util.cfgValue(config, "NonSingleTermYears"))
        int term = Integer.parseInt(policyTerm)
        int minTerm = Integer.parseInt(util.str(rule.get("MinTerm")))
        int maxTerm = Integer.parseInt(util.str(rule.get("MaxTerm")))
        // single premium uses the product's term range; other modes run for the configured fixed term
        if (premiumModeCode == singleMode && (term < minTerm || term > maxTerm)) {
            errors.add(util.fieldError("PolicyTerm", "OUT_OF_RANGE", "PolicyTerm must be between ${minTerm} and ${maxTerm} years for single premium".toString()))
        }
        if (premiumModeCode != singleMode && term != fixedTerm) {
            errors.add(util.fieldError("PolicyTerm", "OUT_OF_RANGE", "PolicyTerm must be ${fixedTerm} for annual or monthly premium".toString()))
        }
    }
    LocalDate dob = util.parseDate(dateOfBirth)
    LocalDate start = util.parseDate(effectiveDate)
    if (dob != null && start != null) {
        int age = (int) ChronoUnit.YEARS.between(dob, start)
        int term = policyTerm && policyTerm.matches("^[0-9]+\$") ? Integer.parseInt(policyTerm) : 0
        if (util.str(rule.get("MinAge")) && age < Integer.parseInt(util.str(rule.get("MinAge")))) {
            errors.add(util.fieldError(risk + ".DateOfBirth", "OUT_OF_RANGE", "Insured age ${age} is below the minimum age ${rule.get('MinAge')}".toString()))
        } else if (util.str(rule.get("MaxAge")) && age > Integer.parseInt(util.str(rule.get("MaxAge")))) {
            errors.add(util.fieldError(risk + ".DateOfBirth", "OUT_OF_RANGE", "Insured age ${age} is above the maximum age ${rule.get('MaxAge')}".toString()))
        } else if (util.str(rule.get("MaxEntryAge")) && age > Integer.parseInt(util.str(rule.get("MaxEntryAge")))) {
            errors.add(util.fieldError(risk + ".DateOfBirth", "OUT_OF_RANGE", "Insured age ${age} is above the maximum entry age ${rule.get('MaxEntryAge')}".toString()))
        } else if (term > 0 && util.str(rule.get("MaxExitAge")) && (age + term) > Integer.parseInt(util.str(rule.get("MaxExitAge")))) {
            errors.add(util.fieldError(risk + ".DateOfBirth", "OUT_OF_RANGE", "Age at exit ${age + term} is above the maximum exit age ${rule.get('MaxExitAge')}".toString()))
        }
    }
    return errors
}
