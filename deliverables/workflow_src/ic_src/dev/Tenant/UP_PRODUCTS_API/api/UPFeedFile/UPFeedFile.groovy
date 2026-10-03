/**
 * Generate the policy feed file (Excel by default, JSON when OutputFormat = "JSON").
 * Request: { "Conditions": {"ProductCode": "FP001"}, "FromRangeConditions": {"EffectiveDate": "..."},
 *            "ToRangeConditions": {"EffectiveDate": "..."}, "SearchType": "Policy", "PageNo": 1, "PageSize": 50,
 *            "OutputFormat": "XLSX" | "JSON" }
 * Commission is not part of the feed file.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.proposal.ProposalSdkClient
import com.insuremo.sdk.services.proposal.model.GroupResult
import com.insuremo.sdk.services.proposal.model.QueryResult
import com.insuremo.sdk.services.proposal.model.SearchCondition
import org.apache.poi.ss.usermodel.Cell
import org.apache.poi.ss.usermodel.Row
import org.apache.poi.ss.usermodel.Sheet
import org.apache.poi.ss.usermodel.Workbook
import org.apache.poi.xssf.usermodel.XSSFWorkbook
import java.io.ByteArrayOutputStream

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPShaper shaper = (UPShaper) getCommonService("UPShaper")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPFeedFile", input)
    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")

    Map<String, Object> conditions = new HashMap<String, Object>()
    Map<String, Object> fromRange = new HashMap<String, Object>()
    Map<String, Object> toRange = new HashMap<String, Object>()
    Map<String, List<Object>> inConditions = new HashMap<String, List<Object>>()
    if (input.get("Conditions") instanceof Map) {
        Map<String, Object> c = (Map<String, Object>) input.get("Conditions")
        if (c.get("ProductCode")) {
            conditions.put("ProductCode", c.get("ProductCode"))
        }
    }
    if (input.get("FromRangeConditions") instanceof Map) {
        fromRange.putAll((Map<String, Object>) input.get("FromRangeConditions"))
    }
    if (input.get("ToRangeConditions") instanceof Map) {
        toRange.putAll((Map<String, Object>) input.get("ToRangeConditions"))
    }
    Map<String, String> config = util.configMap("*")
    boolean proposals = util.str(input.get("SearchType")) == "Proposal"
    if (proposals) {
        List<Object> statuses = new ArrayList<Object>()
        statuses.add(Integer.parseInt(util.cfgValue(config, "ProposalStatusEntry")))
        inConditions.put("PolicyStatus", statuses)
    } else {
        conditions.put("ProposalStatus", Integer.parseInt(util.cfgValue(config, "ProposalStatusIssued")))
    }

    // PageNo and PageSize are required and range checked by the UP_FieldRule table; the total volume is capped by UP_ApiConfig
    int pageSize = Integer.parseInt(util.str(input.get("PageSize")))
    int pageNo = Integer.parseInt(util.str(input.get("PageNo")))
    int maxRecords = Integer.parseInt(util.cfgValue(config, "FeedMaxRecords"))
    int maxPages = Integer.parseInt(util.cfgValue(config, "FeedMaxPages"))

    // columns of the feed file: heading and source path of each column come from UP_FeedColumn
    List<Map<String, Object>> columns = new ArrayList<Map<String, Object>>(util.getRecords("UP_FeedColumn"))
    columns.sort { Map<String, Object> a, Map<String, Object> b -> Integer.parseInt(util.str(a.get("Sequence"))) <=> Integer.parseInt(util.str(b.get("Sequence"))) }
    if (columns.isEmpty()) {
        throw new IllegalStateException("Configuration missing in UP_FeedColumn")
    }
    List<String> headers = new ArrayList<String>()
    for (Map<String, Object> column : columns) {
        headers.add(util.str(column.get("Heading")))
    }
    List<List<String>> rows = new ArrayList<List<String>>()

    boolean hasMore = true
    int pagesRead = 0
    while (hasMore) {
        SearchCondition searchCondition = new SearchCondition()
        searchCondition.setConditions(conditions)
        searchCondition.setFromRangeConditions(fromRange)
        searchCondition.setToRangeConditions(toRange)
        searchCondition.setInConditions(inConditions)
        searchCondition.setPageNo(pageNo)
        searchCondition.setPageSize(pageSize)
        searchCondition.setSortField(util.cfgValue(config, "SearchSortField"))
        searchCondition.setSortType(util.cfgValue(config, "SearchSortType"))
        searchCondition.setModule(util.cfgValue(config, "SearchModule"))
        QueryResult result = proposalSdkClient.proposalApi().newQueryPolicyRequestBuilder()
                .searchCondition(searchCondition).doRequest().getBody()
        long total = result.getTotal() == null ? 0L : result.getTotal().longValue()
        if (total > maxRecords) {
            util.throwValidation([util.fieldError("FromRangeConditions.EffectiveDate", "RANGE_TOO_LARGE", "The selection has ${total} records; the maximum for one feed file is ${maxRecords}. Narrow the date range or product.".toString())])
        }
        List<GroupResult> groups = result.getResults()
        if (groups == null || groups.isEmpty()) {
            break
        }
        for (GroupResult group : groups) {
            List<Map<String, Object>> docs = group.getEsDocs()
            if (docs == null) {
                continue
            }
            for (Map<String, Object> doc : docs) {
                String policyNo = util.str(doc.get("PolicyNo"))
                Map<String, Object> p = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                        .policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
                if (util.str(p.get("ChannelCode")) != util.str(input.get("ChannelCode"))) {
                    continue
                }
                shaper.shapeResponse(p)
                List<String> row = new ArrayList<String>()
                for (Map<String, Object> column : columns) {
                    // a source may list alternatives separated by | (first non-empty wins)
                    String value = ""
                    for (String source : util.str(column.get("Source")).split("\\|")) {
                        value = util.str(util.pathValue(p, source))
                        if (value) {
                            break
                        }
                    }
                    row.add(value)
                }
                rows.add(row)
            }
        }
        pagesRead = pagesRead + 1
        if ((long) pageNo * pageSize >= total || pagesRead >= maxPages) {
            hasMore = false
        } else {
            pageNo = pageNo + 1
        }
    }

    if (util.str(input.get("OutputFormat")).toUpperCase() == "JSON") {
        List<Map<String, Object>> records = new ArrayList<Map<String, Object>>()
        for (List<String> r : rows) {
            Map<String, Object> rec = new LinkedHashMap<String, Object>()
            for (int i = 0; i < headers.size(); i++) {
                rec.put(headers.get(i), r.get(i))
            }
            records.add(rec)
        }
        Map<String, Object> response = new HashMap<String, Object>()
        response.put("Total", records.size())
        response.put("Records", records)
        return response
    }

    Workbook workbook = new XSSFWorkbook()
    Sheet sheet = workbook.createSheet(util.cfgValue(config, "FeedSheetName"))
    Row headerRow = sheet.createRow(0)
    for (int i = 0; i < headers.size(); i++) {
        headerRow.createCell(i).setCellValue(headers.get(i))
    }
    for (int r = 0; r < rows.size(); r++) {
        Row dataRow = sheet.createRow(r + 1)
        for (int c = 0; c < headers.size(); c++) {
            dataRow.createCell(c).setCellValue(rows.get(r).get(c))
        }
    }
    ByteArrayOutputStream bos = new ByteArrayOutputStream()
    workbook.write(bos)
    workbook.close()
    byte[] bytes = bos.toByteArray()
    ICmpHttpServletResponse().reset()
    ICmpHttpServletResponse().setContentType(util.cfgValue(config, "FeedContentType"))
    ICmpHttpServletResponse().setHeader("Content-Disposition", "attachment; filename=\"" + util.cfgValue(config, "FeedFileName") + "\"")
    ICmpHttpServletResponse().setContentLength(bytes.length)
    ICmpHttpServletResponse().getOutputStream().write(bytes)
    ICmpHttpServletResponse().getOutputStream().flush()
    return

} catch (Exception ex) {
    return errorHandler.handle("UPFeedFile", ex)
}
