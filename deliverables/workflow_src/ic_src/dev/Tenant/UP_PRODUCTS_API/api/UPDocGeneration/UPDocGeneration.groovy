/**
 * Generate the application form or the policy certificate as a PDF.
 * Request: { "DocType": "Application" | "Policy", "ProposalNo": "...", "PolicyNo": "..." }
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
    validator.validate("UPDocGeneration", input)
    ((UPAccess) getCommonService("UPAccess")).requireAny()
    UPDocService docs = (UPDocService) getCommonService("UPDocService")
    return docs.generate("UPDocGeneration", util.str(input.get("DocType")), input)

} catch (Exception ex) {
    return errorHandler.handle("UPDocGeneration", ex)
}
