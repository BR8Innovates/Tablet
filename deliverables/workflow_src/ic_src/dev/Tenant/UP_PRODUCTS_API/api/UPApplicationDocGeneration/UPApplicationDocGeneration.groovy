/**
 * Generate the application form of a proposal as a PDF (same request as the PA001 flow).
 * Request: { "proposalNo": "...", "ProductSubcode": "1" }
 * The template is looked up in UP_DocTemplate by ProductCode + ProductSubcode + DocType.
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
    validator.validate("UPApplicationDocGeneration", input)
    ((UPAccess) getCommonService("UPAccess")).requireAny()
    UPDocService docs = (UPDocService) getCommonService("UPDocService")
    return docs.generate("UPApplicationDocGeneration", util.cfg("DocTypeApplication", "*"), input)

} catch (Exception ex) {
    return errorHandler.handle("UPApplicationDocGeneration", ex)
}
