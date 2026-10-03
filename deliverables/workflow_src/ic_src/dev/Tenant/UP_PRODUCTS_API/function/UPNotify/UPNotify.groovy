/**
 * UPNotify - Email / SMS through the tenant's SNS service, driven by UP_NotifyTemplate.
 * A notification never fails the business call: every attempt returns a result row {Event, Recipient, Channel, To (masked), Status}.
 * Status: SENT, DRYRUN (NotifyMode is not LIVE), NO_ADDRESS (no email / mobile known), NO_SMS_TEMPLATE (SmsTemplateCode is NONE) or FAILED.
 * Email is sent with subject and body from the template. The SNS SMS request carries no free text: it names an SMS template (SmsTemplateCode) of the SNS account and its parameters.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.sns.SnsSdkClient
import com.insuremo.sdk.services.sns.model.SendEmailRequest
import com.insuremo.sdk.services.sns.model.SendSMSRequest

String maskEmail(String email) {
    int at = email.indexOf("@")
    return at < 2 ? "***" : email.substring(0, 1) + "***" + email.substring(at)
}

String maskMobile(String mobile) {
    return mobile.length() <= 4 ? "***" : "***" + mobile.substring(mobile.length() - 4)
}

/** Template text with {Name} markers replaced; markers without a value become empty. */
String render(String text, Map<String, String> params) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    return util.fill(text, params).replaceAll("\\{[A-Za-z]+\\}", "")
}

Map<String, Object> resultRow(String event, String recipient, String channel, String to, String status) {
    Map<String, Object> row = new LinkedHashMap<String, Object>()
    row.put("Event", event)
    row.put("Recipient", recipient)
    row.put("Channel", channel)
    row.put("To", to)
    row.put("Status", status)
    return row
}

String sendOne(String channel, String to, String subject, String body, String smsTemplate, Map<String, String> params) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (util.cfg("NotifyMode", "*") != "LIVE") {
        return "DRYRUN"
    }
    SnsSdkClient sns = (SnsSdkClient) getSDK("com.insuremo.sdk.services.sns.SnsSdkClient")
    try {
        if (channel == "EMAIL") {
            Map<String, Object> mail = new LinkedHashMap<String, Object>()
            mail.put("to", Arrays.asList(to))
            mail.put("subject", subject)
            mail.put("content", body)
            if (util.cfg("EmailAccountName", "*") != "NONE") {
                mail.put("accountName", util.cfg("EmailAccountName", "*"))
            }
            SendEmailRequest request = (SendEmailRequest) IComposerJsonUtils.mapToObject(mail, SendEmailRequest.class)
            sns.emailApi().newSendEmailRequestBuilder().requestBody(request).doRequest()
            return "SENT"
        }
        if (smsTemplate == "NONE") {
            return "NO_SMS_TEMPLATE"
        }
        Map<String, Object> sms = new LinkedHashMap<String, Object>()
        sms.put("to", to)
        sms.put("templateCode", smsTemplate)
        sms.put("templateParams", new LinkedHashMap<String, Object>(params))
        if (util.cfg("SmsAccountName", "*") != "NONE") {
            sms.put("accountName", util.cfg("SmsAccountName", "*"))
        }
        SendSMSRequest request = (SendSMSRequest) IComposerJsonUtils.mapToObject(sms, SendSMSRequest.class)
        sns.smsApi().newSendSmsRequestBuilder().requestBody(request).doRequest()
        return "SENT"
    } catch (Exception ex) {
        org.slf4j.LoggerFactory.getLogger("UPNotify").error("notification failed: " + ex.toString())
        return "FAILED"
    }
}

/**
 * Sends every active template of the event. Recipients: a role (all active holders in UP_UserRole), MAKER (the creator of the item, by platform user id) or CUSTOMER (customer map with Email / Mobile).
 * onlyChannels restricts to EMAIL / SMS (empty = both).
 */
List<Map<String, Object>> fire(String event, Map<String, String> params, Map<String, Object> customer, String makerUserId, String onlyChannel) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    List<Map<String, Object>> results = new ArrayList<Map<String, Object>>()
    try {
        for (Map<String, Object> template : util.getRecords("UP_NotifyTemplate")) {
            if (!util.isYes(template.get("IsActive")) || util.str(template.get("Event")) != event) {
                continue
            }
            String channel = util.str(template.get("Channel"))
            if (onlyChannel && onlyChannel != channel) {
                continue
            }
            String recipient = util.str(template.get("Recipient"))
            List<Map<String, Object>> people = new ArrayList<Map<String, Object>>()
            if (recipient == "CUSTOMER") {
                people.add(customer == null ? new HashMap<String, Object>() : customer)
            } else if (recipient == "MAKER") {
                people.add(makerUserId ? access.contactOf(makerUserId) : new HashMap<String, Object>())
            } else {
                people.addAll(access.holdersOf(recipient))
            }
            if (people.isEmpty()) {
                results.add(resultRow(event, recipient, channel, "", "NO_ADDRESS"))
            }
            for (Map<String, Object> person : people) {
                String to = util.str(person.get(channel == "EMAIL" ? "Email" : "Mobile"))
                if (!to) {
                    results.add(resultRow(event, recipient, channel, "", "NO_ADDRESS"))
                    continue
                }
                String status = sendOne(channel, to, render(util.str(template.get("Subject")), params), render(util.str(template.get("Body")), params), util.str(template.get("SmsTemplateCode")), params)
                results.add(resultRow(event, recipient, channel, channel == "EMAIL" ? maskEmail(to) : maskMobile(to), status))
            }
        }
    } catch (Exception ex) {
        org.slf4j.LoggerFactory.getLogger("UPNotify").error("notification set-up problem for " + event + ": " + ex.toString())
        results.add(resultRow(event, "", "", "", "FAILED"))
    }
    return results
}

/** Placeholder values for the templates from a policy / proposal map (stored or shaped). extra overrides / adds values. */
Map<String, String> paramsOf(Map<String, Object> policy, Map<String, String> extra) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    Map<String, String> params = new HashMap<String, String>()
    Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    List<Map<String, Object>> plans = (List<Map<String, Object>>) risk.get("PlanList")
    Map<String, Object> plan = (plans != null && !plans.isEmpty()) ? plans.get(0) : new HashMap<String, Object>()
    params.put("ProposalNo", util.str(policy.get("ProposalNo")))
    params.put("PolicyNo", util.str(policy.get("PolicyNo")))
    params.put("Insured", util.str(risk.get("InsuredName")))
    params.put("Product", products.variantName(util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode"))) ?: util.str(policy.get("ProductCode")))
    params.put("Plan", util.str(plan.get("PlanName") ?: policy.get("PlanId")))
    params.put("Premium", util.fmtMoney(risk.get("DuePremium")))
    params.put("EffectiveDate", util.fmtDate(policy.get("EffectiveDate")))
    params.put("Link", util.cfg("PortalUrl", "*"))
    try {
        params.put("Insurer", util.str(products.carrierOf(util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode"))).get("CarrierName")))
    } catch (Exception ignore) {
        params.put("Insurer", "")
    }
    Map<String, Object> caller = access.me()
    params.put("Checker", util.str(caller.get("DisplayName")))
    params.put("Maker", util.str(caller.get("DisplayName")))
    if (extra != null) {
        params.putAll(extra)
    }
    return params
}

/** Customer contact (Email, Mobile) of a stored proposal / policy, unmasked, for customer alerts. */
Map<String, Object> customerOf(Map<String, Object> storedPolicy) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> contact = new HashMap<String, Object>()
    if (storedPolicy == null || storedPolicy.get("PolicyLobList") == null) {
        return contact
    }
    Map<String, Object> lob = (Map<String, Object>) ((List) storedPolicy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    contact.put("Email", util.str(risk.get("Email")))
    contact.put("Mobile", util.str(risk.get("Mobile")))
    return contact
}
