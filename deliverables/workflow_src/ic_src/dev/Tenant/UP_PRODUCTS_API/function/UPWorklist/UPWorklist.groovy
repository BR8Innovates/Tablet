/**
 * UPWorklist - queues and dashboard figures read from the platform's search index (nothing is stored by this API).
 *   Proposal queue      : proposals by ProposalStatus (pending / issued / rejected), per UP product.
 *   Cancellation queue  : cancellation endorsements by EndoStatus (pending / issued).
 *   Maker filter        : the maker's platform user id is stamped on every proposal in AgentCode by UPProductData.prepareProposal, so "my submissions" is an index search.
 * The index is limited to 1000 rows per query (page size x page number) and holds no premium, so premium and commission are read from the stored policies (capped by DashboardMaxPolicies).
 */
import com.insuremo.sdk.services.proposal.ProposalSdkClient
import com.insuremo.sdk.services.proposal.model.GroupResult
import com.insuremo.sdk.services.proposal.model.QueryResult
import com.insuremo.sdk.services.proposal.model.SearchCondition
import java.math.BigDecimal

/** Distinct product codes enabled for the APIs (UP_ProductMaster). */
List<String> productCodes() {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<String> codes = new ArrayList<String>()
    for (Map<String, Object> row : util.getRecords("ProductMaster")) {
        String code = util.str(row.get("IMOProductCode"))
        if (util.isYes(row.get("IsActive")) && code && !codes.contains(code)) {
            codes.add(code)
        }
    }
    return codes
}

/** Status text for a status filter name, as configured. Returns "" for ALL. */
String proposalStatusCode(String name) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (name == "ISSUED") {
        return util.cfg("ProposalStatusIssued", "*")
    }
    if (name == "REJECTED") {
        return util.cfg("ProposalStatusRejected", "*")
    }
    if (name == "ALL") {
        return ""
    }
    return util.cfg("ProposalStatusPending", "*")
}

Map<String, Object> dateRange(Map<String, Object> input, String key, boolean from) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> range = new HashMap<String, Object>()
    String value = util.str(input.get(from ? "FromDate" : "ToDate"))
    if (value) {
        range.put(key, value.substring(0, 10) + util.cfg(from ? "DayStartTime" : "DayEndTime", "*"))
    }
    return range
}

SearchCondition condition(Map<String, Object> conditions, Map<String, Object> from, Map<String, Object> to, int pageNo, int pageSize, String module) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    SearchCondition sc = new SearchCondition()
    sc.setConditions(conditions)
    sc.setFromRangeConditions(from)
    sc.setToRangeConditions(to)
    sc.setPageNo(pageNo)
    sc.setPageSize(pageSize)
    sc.setSortField(util.cfg("SearchSortField", "*"))
    sc.setSortType(util.cfg("SearchSortType", "*"))
    sc.setModule(module)
    return sc
}

/** One policy-index search: {Total, Docs}. */
Map<String, Object> policySearch(Map<String, Object> conditions, Map<String, Object> from, Map<String, Object> to, int pageNo, int pageSize) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    ProposalSdkClient client = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    QueryResult result = client.proposalApi().newQueryPolicyRequestBuilder().searchCondition(condition(conditions, from, to, pageNo, pageSize, util.cfg("SearchModule", "*"))).doRequest().getBody()
    List<Map<String, Object>> docs = new ArrayList<Map<String, Object>>()
    if (result.getResults() != null) {
        for (GroupResult group : result.getResults()) {
            if (group.getEsDocs() != null) {
                docs.addAll(group.getEsDocs())
            }
        }
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("Total", result.getTotal() == null ? 0 : result.getTotal())
    out.put("Docs", docs)
    return out
}

/** One endorsement-index search: {Total, Docs}. */
Map<String, Object> endoSearch(Map<String, Object> conditions, Map<String, Object> from, Map<String, Object> to, int pageNo, int pageSize) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPPlatformClient client = (UPPlatformClient) getCommonService("UPPlatformClient")
    Map<String, Object> body = new LinkedHashMap<String, Object>()
    body.put("Conditions", conditions)
    body.put("FromRangeConditions", from)
    body.put("ToRangeConditions", to)
    body.put("PageNo", pageNo)
    body.put("PageSize", pageSize)
    body.put("SortField", util.cfg("SearchSortField", "*"))
    body.put("SortType", util.cfg("SearchSortType", "*"))
    body.put("Module", util.cfg("EndoSearchModule", "*"))
    Map<String, Object> response = client.call("POST", util.cfg("EndoSearchPath", "*"), body)
    Map<String, Object> parsed = client.parse(response)
    Map<String, Object> result = (Map<String, Object>) (parsed.get("QueryResult") != null ? parsed.get("QueryResult") : parsed)
    List<Map<String, Object>> docs = new ArrayList<Map<String, Object>>()
    if (result.get("Results") != null) {
        for (Map<String, Object> group : (List<Map<String, Object>>) result.get("Results")) {
            if (group.get("EsDocs") != null) {
                docs.addAll((List<Map<String, Object>>) group.get("EsDocs"))
            }
        }
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("Total", result.get("Total") == null ? 0 : result.get("Total"))
    out.put("Docs", docs)
    return out
}

Map<String, Object> loadPolicy(String proposalNo, String policyNo) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    ProposalSdkClient client = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    if (policyNo) {
        return (Map<String, Object>) client.proposalApi().newLoadRequestBuilder().policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
    }
    return (Map<String, Object>) client.proposalApi().newLoadRequestBuilder().proposalNo(proposalNo).withCodeDesc(util.yes()).doRequest().getBody()
}

/** Display name of a platform user id (UP_UserRole), else the id itself. */
String makerName(String userId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    Map<String, Object> contact = access.contactOf(userId)
    return contact.isEmpty() ? userId : (util.str(contact.get("DisplayName")) ?: util.str(contact.get("UserName")))
}

/** Row shown in a queue, from the stored policy / proposal. */
Map<String, Object> policyRow(Map<String, Object> policy) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
    Map<String, Object> plan = (plans != null && !plans.isEmpty()) ? plans.get(0) : new HashMap<String, Object>()
    Map<String, Object> row = new LinkedHashMap<String, Object>()
    row.put("ProposalNo", util.str(policy.get("ProposalNo")))
    row.put("PolicyNo", util.str(policy.get("PolicyNo")))
    row.put("ProductCode", util.str(policy.get("ProductCode")))
    row.put("ProductSubcode", util.str(policy.get("ProductSubcode")))
    row.put("ProductName", products.variantName(util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode"))))
    row.put("PlanId", util.str(plan.get("PlanId") ?: policy.get("PlanId")))
    row.put("PlanName", util.str(plan.get("PlanName")))
    row.put("InsuredName", util.str(risk.get("InsuredName")))
    row.put("Premium", risk.get("DuePremium"))
    row.put("EffectiveDate", util.str(policy.get("EffectiveDate")).take(10))
    row.put("ProposalDate", util.str(policy.get("FirstDataEntryDate")).take(10))
    row.put("Status", util.str(policy.get("ProposalStatus_CodeDesc")))
    row.put("StatusCode", util.str(policy.get("ProposalStatus")))
    row.put("RejectReason", util.str(policy.get("ProposalRejectDesc")))
    row.put("PolicyStatus", util.str(policy.get("PolicyStatus_CodeDesc")))
    String makerId = util.str(policy.get("AgentCode"))
    row.put("MakerId", makerId)
    row.put("Maker", makerId ? makerName(makerId) : util.str(policy.get("DataEntryUserRealName")))
    products.addCarrier(row, util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    return row
}

int intOf(Object value, int fallback) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    String s = util.str(value)
    return s ? Integer.parseInt(s) : fallback
}

/** Proposal queue: type PROPOSAL (all makers) or MINE (mineUserId is the caller's id), filtered by Status, product and dates. */
Map<String, Object> proposalList(Map<String, Object> input, String mineUserId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    int pageSize = intOf(input.get("PageSize"), Integer.parseInt(util.cfg("WorklistPageSize", "*")))
    int pageNo = intOf(input.get("PageNo"), 1)
    int limit = Integer.parseInt(util.cfg("WorklistMaxRows", "*"))
    if (pageSize * pageNo > limit) {
        util.fail("PageSize x PageNo must not exceed ${limit}".toString())
    }
    String statusCode = proposalStatusCode(util.str(input.get("Status")) ?: "PENDING")
    List<String> products = util.str(input.get("ProductCode")) ? Arrays.asList(util.str(input.get("ProductCode"))) : productCodes()
    long total = 0
    List<Map<String, Object>> docs = new ArrayList<Map<String, Object>>()
    for (String code : products) {
        Map<String, Object> conditions = new HashMap<String, Object>()
        conditions.put("ProductCode", code)
        if (statusCode) {
            conditions.put("ProposalStatus", Integer.parseInt(statusCode))
        }
        if (mineUserId) {
            conditions.put("AgentCode", mineUserId)
        }
        Map<String, Object> found = policySearch(conditions, dateRange(input, "ProposalDate", true), dateRange(input, "ProposalDate", false), 1, Math.min(pageSize * pageNo, 100))
        total += ((Number) found.get("Total")).longValue()
        docs.addAll((List<Map<String, Object>>) found.get("Docs"))
    }
    Collections.sort(docs, new Comparator<Map<String, Object>>() {
        int compare(Map<String, Object> a, Map<String, Object> b) {
            return String.valueOf(b.get("ProposalDate")).compareTo(String.valueOf(a.get("ProposalDate")))
        }
    })
    List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>()
    int from = (pageNo - 1) * pageSize
    for (int i = from; i < docs.size() && i < from + pageSize; i++) {
        Map<String, Object> policy = loadPolicy(util.str(docs.get(i).get("ProposalNo")), "")
        if (policy == null || util.str(policy.get("ChannelCode")) != util.str(input.get("ChannelCode"))) {
            continue
        }
        rows.add(policyRow(policy))
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("Type", mineUserId ? "MINE" : "PROPOSAL")
    out.put("Status", util.str(input.get("Status")) ?: "PENDING")
    out.put("PageNo", pageNo)
    out.put("PageSize", pageSize)
    out.put("Total", total)
    out.put("Records", rows)
    return out
}

/** Cancellation queue: pending (default) or issued cancellation endorsements. */
Map<String, Object> cancellationList(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    int pageSize = intOf(input.get("PageSize"), Integer.parseInt(util.cfg("WorklistPageSize", "*")))
    int pageNo = intOf(input.get("PageNo"), 1)
    int limit = Integer.parseInt(util.cfg("WorklistMaxRows", "*"))
    if (pageSize * pageNo > limit) {
        util.fail("PageSize x PageNo must not exceed ${limit}".toString())
    }
    String status = util.str(input.get("Status")) ?: "PENDING"
    if (status != "PENDING" && status != "ISSUED") {
        util.fail("Status for cancellations must be PENDING or ISSUED (rejected requests are withdrawn by the platform)")
    }
    String endoStatus = util.cfg(status == "ISSUED" ? "EndoStatusIssued" : "EndoStatusPending", "*")
    List<String> products = util.str(input.get("ProductCode")) ? Arrays.asList(util.str(input.get("ProductCode"))) : productCodes()
    long total = 0
    List<Map<String, Object>> docs = new ArrayList<Map<String, Object>>()
    for (String code : products) {
        Map<String, Object> conditions = new HashMap<String, Object>()
        conditions.put("ProductCode", code)
        conditions.put("EndoStatus", endoStatus)
        conditions.put("EndoType", util.cfg("EndoTypeCancelFilter", "*"))
        Map<String, Object> found = endoSearch(conditions, dateRange(input, "FirstDataEntryDate", true), dateRange(input, "FirstDataEntryDate", false), 1, Math.min(pageSize * pageNo, 100))
        total += ((Number) found.get("Total")).longValue()
        docs.addAll((List<Map<String, Object>>) found.get("Docs"))
    }
    Collections.sort(docs, new Comparator<Map<String, Object>>() {
        int compare(Map<String, Object> a, Map<String, Object> b) {
            return String.valueOf(b.get("FirstDataEntryDate")).compareTo(String.valueOf(a.get("FirstDataEntryDate")))
        }
    })
    List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>()
    int from = (pageNo - 1) * pageSize
    for (int i = from; i < docs.size() && i < from + pageSize; i++) {
        Map<String, Object> doc = docs.get(i)
        Map<String, Object> policy = loadPolicy("", util.str(doc.get("PolicyNo")))
        if (policy == null || util.str(policy.get("ChannelCode")) != util.str(input.get("ChannelCode"))) {
            continue
        }
        Map<String, Object> row = policyRow(policy)
        row.put("RequestNo", util.str(doc.get("EndoNo")))
        row.put("RequestStatus", status)
        row.put("RequestedOn", util.str(doc.get("FirstDataEntryDate")).take(10))
        row.put("CancellationDate", util.str(doc.get("EndoEffectiveDate")).take(10))
        rows.add(row)
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("Type", "CANCELLATION")
    out.put("Status", status)
    out.put("PageNo", pageNo)
    out.put("PageSize", pageSize)
    out.put("Total", total)
    out.put("Records", rows)
    return out
}

/** Counts of proposals and cancellations in the date window (mineUserId limits proposals to one maker). */
Map<String, Object> summary(Map<String, Object> input, String mineUserId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    Map<String, Object> proposals = new LinkedHashMap<String, Object>()
    Map<String, Object> byProduct = new LinkedHashMap<String, Object>()
    long cancelPending = 0
    long cancelIssued = 0
    long pending = 0
    long issued = 0
    long rejected = 0
    long oldPending = 0
    String cutoff = java.time.LocalDate.now().minusDays(1).toString() + util.cfg("DayEndTime", "*")
    for (String code : productCodes()) {
        Map<String, Object> base = new HashMap<String, Object>()
        base.put("ProductCode", code)
        if (mineUserId) {
            base.put("AgentCode", mineUserId)
        }
        long[] counts = new long[3]
        String[] names = [util.cfg("ProposalStatusPending", "*"), util.cfg("ProposalStatusIssued", "*"), util.cfg("ProposalStatusRejected", "*")]
        for (int i = 0; i < 3; i++) {
            Map<String, Object> conditions = new HashMap<String, Object>(base)
            conditions.put("ProposalStatus", Integer.parseInt(names[i]))
            counts[i] = ((Number) policySearch(conditions, dateRange(input, "ProposalDate", true), dateRange(input, "ProposalDate", false), 1, 1).get("Total")).longValue()
        }
        pending += counts[0]
        issued += counts[1]
        rejected += counts[2]
        if (counts[0] > 0) {
            Map<String, Object> conditions = new HashMap<String, Object>(base)
            conditions.put("ProposalStatus", Integer.parseInt(names[0]))
            Map<String, Object> older = new HashMap<String, Object>()
            older.put("ProposalDate", cutoff)
            oldPending += ((Number) policySearch(conditions, new HashMap<String, Object>(), older, 1, 1).get("Total")).longValue()
        }
        Map<String, Object> line = new LinkedHashMap<String, Object>()
        line.put("Pending", counts[0])
        line.put("Issued", counts[1])
        line.put("Rejected", counts[2])
        byProduct.put(code, line)
        Map<String, Object> endo = new HashMap<String, Object>()
        endo.put("ProductCode", code)
        endo.put("EndoType", util.cfg("EndoTypeCancelFilter", "*"))
        endo.put("EndoStatus", util.cfg("EndoStatusPending", "*"))
        cancelPending += ((Number) endoSearch(endo, new HashMap<String, Object>(), new HashMap<String, Object>(), 1, 1).get("Total")).longValue()
        Map<String, Object> done = new HashMap<String, Object>(endo)
        done.put("EndoStatus", util.cfg("EndoStatusIssued", "*"))
        cancelIssued += ((Number) endoSearch(done, dateRange(input, "FirstDataEntryDate", true), dateRange(input, "FirstDataEntryDate", false), 1, 1).get("Total")).longValue()
    }
    proposals.put("Pending", pending)
    proposals.put("PendingOlderThanOneDay", oldPending)
    proposals.put("Issued", issued)
    proposals.put("Rejected", rejected)
    proposals.put("Submitted", pending + issued + rejected)
    out.put("Proposals", proposals)
    Map<String, Object> cancellations = new LinkedHashMap<String, Object>()
    cancellations.put("Pending", cancelPending)
    cancellations.put("Issued", cancelIssued)
    out.put("Cancellations", cancellations)
    out.put("ByProduct", byProduct)
    return out
}

/** Premium and commission of the issued policies of one product in the window, by plan. Capped at DashboardMaxPolicies newest policies (Truncated tells when the cap applied). */
Map<String, Object> commissionSection(Map<String, Object> input, String productCode, String mineUserId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    int cap = Integer.parseInt(util.cfg("DashboardMaxPolicies", "*"))
    Map<String, Object> conditions = new HashMap<String, Object>()
    conditions.put("ProductCode", productCode)
    conditions.put("ProposalStatus", Integer.parseInt(util.cfg("ProposalStatusIssued", "*")))
    if (mineUserId) {
        conditions.put("AgentCode", mineUserId)
    }
    Map<String, Object> found = policySearch(conditions, dateRange(input, "EffectiveDate", true), dateRange(input, "EffectiveDate", false), 1, Math.min(cap, 100))
    long total = ((Number) found.get("Total")).longValue()
    BigDecimal premium = BigDecimal.ZERO
    BigDecimal commission = BigDecimal.ZERO
    BigDecimal cancelledPremium = BigDecimal.ZERO
    BigDecimal cancelledCommission = BigDecimal.ZERO
    long counted = 0
    long cancelled = 0
    Map<String, Map<String, Object>> byPlan = new LinkedHashMap<String, Map<String, Object>>()
    for (Map<String, Object> doc : (List<Map<String, Object>>) found.get("Docs")) {
        Map<String, Object> policy = loadPolicy("", util.str(doc.get("PolicyNo")))
        if (policy == null || util.str(policy.get("ChannelCode")) != util.str(input.get("ChannelCode"))) {
            continue
        }
        Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
        Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
        List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
        Map<String, Object> plan = (plans != null && !plans.isEmpty()) ? plans.get(0) : new HashMap<String, Object>()
        BigDecimal p = util.toDecimal(risk.get("DuePremium"))
        BigDecimal c = util.toDecimal(risk.get("Commission") != null ? risk.get("Commission") : lob.get("Commission"))
        String planName = util.str(plan.get("PlanName") ?: policy.get("PlanId"))
        boolean isCancelled = util.str(policy.get("PolicyStatus")) != util.cfg("PolicyStatusInforce", "*")
        Map<String, Object> line = byPlan.get(planName)
        if (line == null) {
            line = new LinkedHashMap<String, Object>()
            line.put("PlanName", planName)
            line.put("Policies", 0L)
            line.put("Premium", BigDecimal.ZERO)
            line.put("Commission", BigDecimal.ZERO)
            byPlan.put(planName, line)
        }
        counted++
        if (isCancelled) {
            cancelled++
            cancelledPremium = cancelledPremium.add(p)
            cancelledCommission = cancelledCommission.add(c)
            continue
        }
        premium = premium.add(p)
        commission = commission.add(c)
        line.put("Policies", ((Long) line.get("Policies")) + 1)
        line.put("Premium", ((BigDecimal) line.get("Premium")).add(p))
        line.put("Commission", ((BigDecimal) line.get("Commission")).add(c))
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("ProductCode", productCode)
    out.put("IssuedInWindow", total)
    out.put("Counted", counted)
    out.put("Truncated", total > counted)
    out.put("InForce", counted - cancelled)
    out.put("Cancelled", cancelled)
    out.put("Premium", premium)
    out.put("Commission", commission)
    out.put("CancelledPremium", cancelledPremium)
    out.put("CancelledCommission", cancelledCommission)
    out.put("ByPlan", new ArrayList<Map<String, Object>>(byPlan.values()))
    return out
}
