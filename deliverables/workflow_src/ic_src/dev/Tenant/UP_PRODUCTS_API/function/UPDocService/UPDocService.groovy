/**
 * UPDocService - builds the application form or the policy certificate as a PDF through the print service.
 * Shared by UPDocGeneration and UPApplicationDocGeneration. Every setting (template version, print URL,
 * export type, storage, mode, file name) comes from UP_ApiConfig, the template name from UP_DocTemplate.
 */
import com.insuremo.icomposer.utils.IComposerAppContext
import com.insuremo.icomposer.utils.IComposerRestTemplateManager
import com.insuremo.sdk.services.proposal.ProposalSdkClient
import org.springframework.http.HttpEntity
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpMethod
import org.springframework.http.ResponseEntity
import org.springframework.web.client.RestTemplate

/** Returns the PDF (HttpEntity), the print data when PreviewData is the TrueValue, or a 404 body. */
Object generate(String apiName, String docType, Map<String, Object> input) {
    UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPDocBuilder builder = (UPDocBuilder) getCommonService("UPDocBuilder")
    UPShaper shaper = (UPShaper) getCommonService("UPShaper")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    String applicationType = util.cfg("DocTypeApplication", "*")
    String policyType = util.cfg("DocTypePolicy", "*")
    String policyNo = util.str(input.get("PolicyNo"))
    String proposalNo = util.str(input.get("ProposalNo") ?: input.get("proposalNo"))
    if (docType != applicationType && docType != policyType) {
        util.fail("DocType must be '${applicationType}' or '${policyType}'".toString())
    }
    boolean forPolicy = docType == policyType
    if (forPolicy && !policyNo) {
        util.fail("PolicyNo is required when DocType is ${policyType}".toString())
    }
    if (!forPolicy && !proposalNo) {
        util.fail("ProposalNo is required when DocType is ${applicationType}".toString())
    }

    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    Map<String, Object> policyObject
    if (forPolicy) {
        policyObject = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                .policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
    } else {
        policyObject = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder()
                .proposalNo(proposalNo).withCodeDesc(util.yes()).doRequest().getBody()
    }
    if (policyObject == null) {
        return errorHandler.notFound(apiName, "No ${forPolicy ? 'policy' : 'proposal'} found for ${forPolicy ? policyNo : proposalNo}".toString())
    }
    validator.requireChannel(policyObject, util.str(input.get("ChannelCode")))
    shaper.shapeResponse(policyObject)

    String productCode = util.str(policyObject.get("ProductCode"))
    String subcode = util.str(input.get("ProductSubcode") ?: policyObject.get("ProductSubcode"))
    Map<String, Object> filters = new HashMap<String, Object>()
    filters.put("ProductCode", productCode)
    filters.put("ProductSubcode", subcode)
    filters.put("DocType", docType)
    List<Map<String, Object>> templates = util.filterRecords("DocTemplate", filters)
    if (templates.isEmpty()) {
        util.fail("No ${docType} template configured for ${productCode} / ${subcode}".toString())
    }
    String templateName = util.str(templates.get(0).get("TemplateName"))

    Map<String, Object> printData = builder.buildPrintData(policyObject, docType)
    if (util.isYes(input.get("PreviewData"))) {
        // returns the data that is merged into the template, handy for template design and testing
        Map<String, Object> preview = new HashMap<String, Object>()
        preview.put("TemplateName", templateName)
        preview.put("PrintData", printData)
        return preview
    }

    Map<String, String> config = util.configMap(productCode)
    Map<String, Object> printRequest = new HashMap<String, Object>()
    printRequest.put("template_name", templateName)
    printRequest.put("template_version", util.cfgValue(config, "TemplateVersion"))
    printRequest.put("print_data", printData)
    printRequest.put("export_file_type", util.cfgValue(config, "PrintExportType"))
    printRequest.put("storage_config", util.cfgValue(config, "PrintStorage"))
    printRequest.put("async_or_sync", util.cfgValue(config, "PrintMode"))

    String printUrl = util.cfgValue(config, "PrintUrl")
    util.requireAllowedHost(printUrl)
    HttpHeaders requestHeaders = new HttpHeaders()
    requestHeaders.set("Content-Type", "application/json")
    requestHeaders.set("x-mo-tenant-id", IComposerAppContext.getTenantCode())
    requestHeaders.set("Authorization", "Bearer " + IComposerAppContext.getAccessToken())
    HttpEntity<Map<String, Object>> entity = new HttpEntity<Map<String, Object>>(printRequest, requestHeaders)
    RestTemplate restTemplate = (RestTemplate) IComposerRestTemplateManager.remoteCall()
    ResponseEntity<Map> printResponse = restTemplate.exchange(printUrl, HttpMethod.POST, entity, Map.class)
    Map<String, Object> printBody = (Map<String, Object>) printResponse.getBody()
    Map<String, Object> printResult = (Map<String, Object>) (printBody.get("data") ?: printBody)
    String content = util.str(printResult.get("target_file_content"))
    if (!content) {
        util.fail("Print service returned no document for template ${templateName}: ${util.str(printResult.get('print_status'))}".toString())
    }
    byte[] pdf = java.util.Base64.getDecoder().decode(content)

    HttpHeaders headers = new HttpHeaders()
    String fileName = util.fill(util.cfgValue(config, "DocFileNamePattern"), ["docType": docType, "number": forPolicy ? policyNo : proposalNo])
    headers.set("Content-Type", util.cfgValue(config, "DocContentType"))
    headers.set("Content-Disposition", "attachment; filename=${fileName}".toString())
    return new HttpEntity<byte[]>(pdf, headers)
}
