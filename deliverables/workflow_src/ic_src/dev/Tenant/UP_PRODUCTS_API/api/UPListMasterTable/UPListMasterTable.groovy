/**
 * List master data for the front-end dropdowns.
 * Request: { "DataTableName": "Relationship", "Id": "2" (optional) }.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils

UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPSecurity security = (UPSecurity) getCommonService("UPSecurity")
    Map<String, Object> input = security.readInput(RequestBody())
    if (input == null) {
        input = new HashMap<String, Object>()
    }
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    validator.validate("UPListMasterTable", input)
    String tableName = util.str(input.get("DataTableName"))
    List<String> allowed = Arrays.asList(util.cfg("MasterTables", "*").split(","))
    if (!tableName || !allowed.contains(tableName)) {
        util.fail("DataTableName is required and must be one of: ${allowed.join(', ')}".toString())
    }
    String id = util.str(input.get("Id"))
    List<Map<String, Object>> result = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> record : util.getRecords(tableName)) {
        if (id && util.str(record.get("Id")) != id) {
            continue
        }
        Map<String, Object> row = new LinkedHashMap<String, Object>(record)
        row.remove("Commission")
        result.add(row)
    }
    return result

} catch (Exception ex) {
    return errorHandler.handle("UPListMasterTable", ex)
}
