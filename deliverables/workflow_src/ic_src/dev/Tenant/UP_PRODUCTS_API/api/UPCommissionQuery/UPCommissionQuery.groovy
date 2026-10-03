/**
 * Commission query - the only API that returns commission (all other APIs hide it).
 *
 * 1. By policy:         { "PolicyNo": "POFP00100000013" }
 * 2. By configuration:  { "ProductCode": "FP001", "ProductSubcode": "1", "PlanId": "2" (optional) }
 * 3. By period:         { "ProductCode": "FP001" (optional), "FromDate": "2026-10-01", "ToDate": "2026-10-31", "PageNo": 1, "PageSize": 50 }
 *
 * Commission is configured per product / variant / plan in the ProductPlanRelation table (column Commission).
 * It is written onto the policy when the premium is calculated, so a policy keeps the commission it was issued with.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.proposal.ProposalSdkClient
import com.insuremo.sdk.services.proposal.model.GroupResult
import com.insuremo.sdk.services.proposal.model.QueryResult
import com.insuremo.sdk.services.proposal.model.SearchCondition

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPDocBuilder builder = (UPDocBuilder) getCommonService("UPDocBuilder")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPCommissionQuery", input)
    ((UPAccess) getCommonService("UPAccess")).requireAny()
    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")

    String policyNo = util.str(input.get("PolicyNo"))
    String productCode = util.str(input.get("ProductCode"))
    String subcode = util.str(input.get("ProductSubcode"))

    if (policyNo) {
        Map<String, Object> policy = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                .policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
        if (policy == null) {
            return errorHandler.notFound("UPCommissionQuery", "No policy found for ${policyNo}".toString())
        }
        validator.requireChannel(policy, util.str(input.get("ChannelCode")))
        return builder.commissionOfPolicy(policy)
    }

    if (productCode && !input.get("FromDate")) {
        // configuration view
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>()
        Map<String, Object> filters = new HashMap<String, Object>()
        filters.put("IMOProductCode", productCode)
        if (subcode) {
            filters.put("CarrierProductCode", subcode)
        }
        if (input.get("PlanId")) {
            filters.put("IMOPlanCode", util.str(input.get("PlanId")))
        }
        for (Map<String, Object> r : util.filterRecords("ProductPlanRelation", filters)) {
            Map<String, Object> row = new LinkedHashMap<String, Object>()
            row.put("ProductCode", util.str(r.get("IMOProductCode")))
            row.put("ProductSubcode", util.str(r.get("CarrierProductCode")))
            ((UPProductData) getCommonService("UPProductData")).addCarrier(row, util.str(r.get("IMOProductCode")), util.str(r.get("CarrierProductCode")))
            row.put("PlanId", util.str(r.get("IMOPlanCode")))
            row.put("PlanName", util.str(r.get("IMOPlanName")))
            row.put("PremiumModeCode", util.str(r.get("PremiumModeCode")))
            row.put("Premium", util.fmtMoney(r.get("Premium")))
            row.put("Commission", util.fmtMoney(r.get("Commission")))
            row.put("CommissionRate", builder.rate(r.get("Commission"), r.get("Premium")))
            rows.add(row)
        }
        Map<String, Object> response = new LinkedHashMap<String, Object>()
        response.put("Source", "Configuration (ProductPlanRelation)")
        response.put("Records", rows)
        return response
    }

    if (!input.get("FromDate") || !input.get("ToDate")) {
        util.fail("Provide PolicyNo, or ProductCode (+ ProductSubcode / PlanId), or FromDate and ToDate")
    }
    // period view
    Map<String, Object> conditions = new HashMap<String, Object>()
    conditions.put("ProposalStatus", Integer.parseInt(util.cfg("ProposalStatusIssued", "*")))
    if (productCode) {
        conditions.put("ProductCode", productCode)
    }
    Map<String, Object> fromRange = new HashMap<String, Object>()
    fromRange.put("EffectiveDate", util.str(input.get("FromDate")).substring(0, 10) + util.cfg("DayStartTime", "*"))
    Map<String, Object> toRange = new HashMap<String, Object>()
    toRange.put("EffectiveDate", util.str(input.get("ToDate")).substring(0, 10) + util.cfg("DayEndTime", "*"))
    Map<String, String> config = util.configMap("*")
    int pageSize = Integer.parseInt(input.get("PageSize") ? util.str(input.get("PageSize")) : util.cfgValue(config, "CommissionDefaultPageSize"))
    int pageNo = Integer.parseInt(input.get("PageNo") ? util.str(input.get("PageNo")) : util.cfgValue(config, "CommissionDefaultPageNo"))
    SearchCondition searchCondition = new SearchCondition()
    searchCondition.setConditions(conditions)
    searchCondition.setFromRangeConditions(fromRange)
    searchCondition.setToRangeConditions(toRange)
    searchCondition.setPageNo(pageNo)
    searchCondition.setPageSize(pageSize)
    searchCondition.setSortField(util.cfgValue(config, "SearchSortField"))
    searchCondition.setSortType(util.cfgValue(config, "SearchSortType"))
    searchCondition.setModule(util.cfgValue(config, "SearchModule"))
    QueryResult result = proposalSdkClient.proposalApi().newQueryPolicyRequestBuilder().searchCondition(searchCondition).doRequest().getBody()
    List<Map<String, Object>> records = new ArrayList<Map<String, Object>>()
    BigDecimal totalPremium = BigDecimal.ZERO
    BigDecimal totalCommission = BigDecimal.ZERO
    if (result.getResults() != null) {
        for (GroupResult group : result.getResults()) {
            if (group.getEsDocs() == null) {
                continue
            }
            for (Map<String, Object> doc : group.getEsDocs()) {
                Map<String, Object> policy = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                        .policyNo(util.str(doc.get("PolicyNo"))).withCodeDesc(util.yes()).doRequest().getBody()
                if (util.str(policy.get("ChannelCode")) != util.str(input.get("ChannelCode"))) {
                    continue
                }
                Map<String, Object> row = builder.commissionOfPolicy(policy)
                totalPremium = totalPremium.add(util.toDecimal(String.valueOf(row.get("PremiumRaw"))))
                totalCommission = totalCommission.add(util.toDecimal(String.valueOf(row.get("CommissionRaw"))))
                row.remove("PremiumRaw")
                row.remove("CommissionRaw")
                records.add(row)
            }
        }
    }
    Map<String, Object> response = new LinkedHashMap<String, Object>()
    response.put("Source", "Issued policies")
    response.put("FromDate", util.str(input.get("FromDate")))
    response.put("ToDate", util.str(input.get("ToDate")))
    response.put("Total", result.getTotal())
    response.put("PageNo", pageNo)
    response.put("PageTotalPremium", util.fmtMoney(totalPremium))
    response.put("PageTotalCommission", util.fmtMoney(totalCommission))
    response.put("Records", records)
    return response
} catch (Exception ex) {
    return errorHandler.handle("UPCommissionQuery", ex)
}
