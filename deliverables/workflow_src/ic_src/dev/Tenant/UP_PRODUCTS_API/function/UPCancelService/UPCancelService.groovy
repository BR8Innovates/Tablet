/**
 * UPCancelService - cancellation in two steps (Checker, then Approver).
 *
 * The request itself is the platform's own pending cancellation endorsement: the Checker creates it (the endorsement
 * number is the RequestNo), the Approver approves it (calculate, validate, issue) or rejects it (suspend). No premium
 * is calculated by the platform here; the refund is calculated by UPDataUtil.refundCalc from the product rules.
 * Every code (statuses, types, paths) comes from UP_ApiConfig.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.proposal.ProposalSdkClient
import java.math.BigDecimal
import java.time.LocalDate
import java.time.temporal.ChronoUnit

/** The issued policy named by PolicyNo or ProposalNo, checked against the caller's channel. Returns null when it does not exist. */
Map<String, Object> resolvePolicy(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    String policyNo = util.str(input.get("PolicyNo"))
    String proposalNo = util.str(input.get("ProposalNo"))
    Map<String, Object> stored
    if (policyNo) {
        stored = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder().policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
    } else {
        stored = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder().proposalNo(proposalNo).withCodeDesc(util.yes()).doRequest().getBody()
        if (stored != null) {
            if (!util.str(stored.get("PolicyNo"))) {
                throw new IllegalArgumentException("CONFLICT:Proposal ${proposalNo} has not been issued, so there is no policy to cancel".toString())
            }
            stored = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder().policyNo(util.str(stored.get("PolicyNo"))).withCodeDesc(util.yes()).doRequest().getBody()
        }
    }
    if (stored == null) {
        return null
    }
    validator.requireChannel(stored, util.str(input.get("ChannelCode")))
    if (util.filterRecords("ProductMaster", ["IMOProductCode": util.str(stored.get("ProductCode"))]).isEmpty()) {
        util.fail("Cancellation through this API is not enabled for product ${util.str(stored.get('ProductCode'))}".toString())
    }
    return stored
}

/** The pending cancellation endorsement of the policy, or null. Another kind of pending endorsement blocks the request. */
Map<String, Object> pendingCancellation(Map<String, Object> policy) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    UPPlatformClient client = (UPPlatformClient) getCommonService("UPPlatformClient")
    Map<String, String> config = util.configMap("*")
    // the endorsement service needs the signed policy id ("id,signature", sent as is: the client encodes the URL once), which only the platform's own load returns
    Map<String, Object> signed = client.parse(client.call("GET", util.cfgValue(config, "ProposalLoadPath") + "?policyNo=" + util.str(policy.get("PolicyNo")), null))
    Map<String, Object> pending = client.parse(client.call("GET", util.cfgValue(config, "EndoBasePath") + "/queryPendingEndo?policyId=" + util.str(signed.get("PolicyId")), null))
    if (pending.get("EndoNo") == null) {
        return null
    }
    if (util.str(pending.get("EndoType")) != util.cfgValue(config, "EndoTypeCancel")) {
        throw new IllegalArgumentException("CONFLICT:Policy ${util.str(policy.get('PolicyNo'))} already has another endorsement in progress".toString())
    }
    return pending
}

/** Cancellation date used for the refund: the endorsement effective date, or the start of the policy for a free-look cancellation. */
LocalDate cancellationDate(Map<String, Object> endorsement) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    return util.parseDate(endorsement.get("EndoEffectiveDate"))
}

/** Policy information block shared by both responses. */
Map<String, Object> policyInfo(Map<String, Object> policy) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    Map<String, Object> info = new LinkedHashMap<String, Object>()
    info.put("PolicyNo", util.str(policy.get("PolicyNo")))
    info.put("ProposalNo", util.str(policy.get("ProposalNo")))
    info.put("ProductCode", util.str(policy.get("ProductCode")))
    info.put("ProductSubcode", util.str(policy.get("ProductSubcode")))
    info.put("PlanId", util.str(policy.get("PlanId")))
    info.put("InsuredName", util.str(risk.get("InsuredName")))
    info.put("EffectiveDate", util.str(policy.get("EffectiveDate")).take(10))
    info.put("ExpiryDate", util.str(policy.get("ExpiryDate")).take(10))
    info.put("ChannelCode", util.str(policy.get("ChannelCode")))
    products.addCarrier(info, util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    return info
}

Map<String, Object> policyStatus(Map<String, Object> policy) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    Map<String, Object> status = new LinkedHashMap<String, Object>()
    status.put("Code", util.str(policy.get("PolicyStatus")))
    status.put("Description", util.str(policy.get("PolicyStatus_CodeDesc")))
    return status
}

/** Creates the pending cancellation endorsement (the request). No premium is calculated by the platform here. */
Map<String, Object> createRequest(Map<String, Object> policy, String effectiveDate, boolean freeLook, String reason) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    UPPlatformClient client = (UPPlatformClient) getCommonService("UPPlatformClient")
    Map<String, String> config = util.configMap("*")
    Map<String, Object> envelope = new LinkedHashMap<String, Object>()
    envelope.put("EndoEffectiveDate", effectiveDate)
    envelope.put("EndoType", util.cfgValue(config, "EndoTypeCancel"))
    envelope.put("CancelType", freeLook ? util.cfgValue(config, "CancelTypeFreeLook") : util.cfgValue(config, "CancelTypeProRata"))
    envelope.put("CancelReasonCode", util.cfgValue(config, "CancelReasonCode"))
    envelope.put("OtherCancelReason", reason)
    envelope.put("PolicyNo", util.str(policy.get("PolicyNo")))
    envelope.put("ProductId", policy.get("ProductId"))
    envelope.put("ProductCode", policy.get("ProductCode"))
    List<Map<String, Object>> payInfo = new ArrayList<Map<String, Object>>()
    Map<String, Object> pay = new HashMap<String, Object>()
    pay.put("PayModeCode", util.cfgValue(config, "CancelPayMode"))
    pay.put("IsInstallment", util.cfgValue(config, "CancelInstallmentFlag"))
    pay.put("InstallmentType", util.cfgValue(config, "CancelInstallmentType"))
    payInfo.add(pay)
    envelope.put("EndorsementPaymentInfoList", payInfo)
    Map<String, Object> created = client.call("POST", util.cfgValue(config, "EndoBasePath") + "/createEx", envelope)
    if (created.get("status") != 200) {
        throw new IllegalArgumentException("CONFLICT:The cancellation request could not be created: ${util.str(created.get('body')).take(Integer.parseInt(util.cfgValue(config, 'PlatformErrorMaxLength')))}".toString())
    }
    return client.parse(created)
}

/** Withdraws a pending endorsement (reject, or before it is replaced on approval). */
void suspend(Map<String, Object> endorsement) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    UPPlatformClient client = (UPPlatformClient) getCommonService("UPPlatformClient")
    Map<String, Object> suspended = client.call("POST", util.cfg("EndoBasePath", "*") + "/suspendEndorsement?endoId=" + util.str(endorsement.get("EndoId")), null)
    if (suspended.get("status") != 200 && suspended.get("status") != 204) {
        throw new IllegalArgumentException("CONFLICT:The request ${util.str(endorsement.get('EndoNo'))} could not be closed".toString())
    }
}

/** Checker: creates (or returns) the pending cancellation request and shows premium and refund details. */
Map<String, Object> check(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    UPPlatformClient client = (UPPlatformClient) getCommonService("UPPlatformClient")
    UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
    Map<String, String> config = util.configMap("*")
    Map<String, Object> policy = resolvePolicy(input)
    if (policy == null) {
        return errorHandler.notFound("UPCancelCheck", "No policy found for ${util.str(input.get('PolicyNo') ?: input.get('ProposalNo'))}".toString())
    }
    String policyNo = util.str(policy.get("PolicyNo"))
    String inforce = util.cfgValue(config, "PolicyStatusInforce")
    if (util.str(policy.get("PolicyStatus")) != inforce) {
        throw new IllegalArgumentException("CONFLICT:Policy ${policyNo} cannot be cancelled: status is ${util.str(policy.get('PolicyStatus_CodeDesc'))}".toString())
    }
    LocalDate cancelDate = util.parseDate(input.get("CancellationDate"))
    String reason = util.str(input.get("CancelReason"))
    Map<String, Object> endorsement = pendingCancellation(policy)
    boolean existing = endorsement != null
    Map<String, Object> refund
    if (existing) {
        // the request already exists: show it again, calculated for the date it was created with
        refund = refundCalc(policy, cancellationDate(endorsement))
    } else {
        refund = refundCalc(policy, cancelDate)
        boolean freeLook = util.str(refund.get("CancellationType")) == util.cfgValue(config, "RefundTypeFreeLook")
        endorsement = createRequest(policy, freeLook ? util.str(policy.get("EffectiveDate")).take(10) : cancelDate.toString(), freeLook, reason)
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("RequestNo", util.str(endorsement.get("EndoNo")))
    out.put("RequestStatus", util.cfgValue(config, "RequestStatusPending"))
    out.put("RequestExists", existing ? util.yes() : util.no())
    out.put("PolicyInfo", policyInfo(policy))
    ((UPProductData) getCommonService("UPProductData")).addCarrier(out, util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    out.put("PolicyStatus", policyStatus(policy))
    out.put("CancelReason", util.str(endorsement.get("OtherCancelReason") ?: reason))
    out.put("CancellationDate", cancelDate == null || existing ? util.str(endorsement.get("EndoEffectiveDate")).take(10) : cancelDate.toString())
    Map<String, Object> premium = new LinkedHashMap<String, Object>()
    premium.put("Premium", refund.get("Premium"))
    premium.put("PolicyPeriodDays", refund.get("PolicyPeriodDays"))
    premium.put("DaysSinceCommencement", refund.get("DaysSinceCommencement"))
    premium.put("UnexpiredDays", refund.get("UnexpiredDays"))
    premium.put("ProRataPremium", refund.get("ProRataPremium"))
    premium.put("FreeLookDays", refund.get("FreeLookDays"))
    out.put("PremiumDetails", premium)
    Map<String, Object> refundDetails = new LinkedHashMap<String, Object>()
    refundDetails.put("CancellationType", refund.get("CancellationType"))
    refundDetails.put("RefundPercent", refund.get("RefundPercent"))
    refundDetails.put("RefundPremium", refund.get("RefundPremium"))
    out.put("RefundDetails", refundDetails)
    if (!existing) {
        UPNotify notify = (UPNotify) getCommonService("UPNotify")
        UPAccess access = (UPAccess) getCommonService("UPAccess")
        Map<String, String> extra = new HashMap<String, String>()
        extra.put("RequestNo", util.str(endorsement.get("EndoNo")))
        extra.put("Reason", reason)
        extra.put("Refund", util.fmtMoney(refund.get("RefundPremium")))
        out.put("Notifications", notify.fire("CANCEL_REQUESTED", notify.paramsOf(policy, extra), null, util.str(access.me().get("UserId")), ""))
    }
    return out
}

/** Checker view of a pending request (nothing is created): who asked, why, and the refund an approval would pay. */
Map<String, Object> detail(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    Map<String, String> config = util.configMap("*")
    Map<String, Object> policy = resolvePolicy(input)
    if (policy == null) {
        return errorHandler.notFound("UPCancelDetail", "No policy found for ${util.str(input.get('PolicyNo') ?: input.get('ProposalNo'))}".toString())
    }
    Map<String, Object> endorsement = pendingCancellation(policy)
    if (endorsement == null) {
        return errorHandler.notFound("UPCancelDetail", "No pending cancellation request for policy ${util.str(policy.get('PolicyNo'))}".toString())
    }
    Map<String, Object> refund = refundCalc(policy, cancellationDate(endorsement))
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("RequestNo", util.str(endorsement.get("EndoNo")))
    out.put("RequestStatus", util.cfgValue(config, "RequestStatusPending"))
    out.put("PolicyInfo", policyInfo(policy))
    ((UPProductData) getCommonService("UPProductData")).addCarrier(out, util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    out.put("PolicyStatus", policyStatus(policy))
    out.put("CancelReason", util.str(endorsement.get("OtherCancelReason")))
    out.put("CancellationDate", util.str(endorsement.get("EndoEffectiveDate")).take(10))
    String requesterId = util.str(endorsement.get("DataEntryUserId"))
    out.put("RequestedBy", requesterId ? ((UPWorklist) getCommonService("UPWorklist")).makerName(requesterId) : util.str(endorsement.get("DataEntryUserRealName")))
    out.put("RequestedOn", util.str(endorsement.get("InsertTime")).take(10))
    out.put("CanDecide", requesterId != util.str(access.me().get("UserId")) || util.isYes(util.cfg("AllowSelfApproval", "*")) || !util.isYes(util.cfg("RoleEnforcement", "*")) ? util.yes() : util.no())
    Map<String, Object> premium = new LinkedHashMap<String, Object>()
    premium.put("Premium", refund.get("Premium"))
    premium.put("PolicyPeriodDays", refund.get("PolicyPeriodDays"))
    premium.put("DaysSinceCommencement", refund.get("DaysSinceCommencement"))
    premium.put("UnexpiredDays", refund.get("UnexpiredDays"))
    premium.put("ProRataPremium", refund.get("ProRataPremium"))
    premium.put("FreeLookDays", refund.get("FreeLookDays"))
    out.put("PremiumDetails", premium)
    Map<String, Object> refundDetails = new LinkedHashMap<String, Object>()
    refundDetails.put("CancellationType", refund.get("CancellationType"))
    refundDetails.put("RefundPercent", refund.get("RefundPercent"))
    refundDetails.put("RefundPremium", refund.get("RefundPremium"))
    out.put("RefundDetails", refundDetails)
    return out
}

/** Approver: approves (cancels the policy through the platform) or rejects the pending request named by RequestNo. */
Map<String, Object> decide(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPValidator validator = (UPValidator) getCommonService("UPValidator")
    UPPlatformClient client = (UPPlatformClient) getCommonService("UPPlatformClient")
    UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
    ProposalSdkClient proposalSdkClient = (ProposalSdkClient) getSDK("com.insuremo.sdk.services.proposal.ProposalSdkClient")
    Map<String, String> config = util.configMap("*")
    Map<String, Object> policy = resolvePolicy(input)
    if (policy == null) {
        return errorHandler.notFound("UPCancelApprove", "No policy found for ${util.str(input.get('PolicyNo') ?: input.get('ProposalNo'))}".toString())
    }
    String policyNo = util.str(policy.get("PolicyNo"))
    String requestNo = util.str(input.get("RequestNo"))
    Map<String, Object> endorsement = pendingCancellation(policy)
    if (endorsement == null || util.str(endorsement.get("EndoNo")) != requestNo) {
        return errorHandler.notFound("UPCancelApprove", "No pending cancellation request ${requestNo} for policy ${policyNo}".toString())
    }
    String requesterId = util.str(endorsement.get("DataEntryUserId"))
    ((UPAccess) getCommonService("UPAccess")).requireNotCreator(((UPAccess) getCommonService("UPAccess")).me(), requesterId)
    Map<String, Object> customer = ((UPNotify) getCommonService("UPNotify")).customerOf(policy)
    String endoBase = util.cfgValue(config, "EndoBasePath")
    boolean approve = util.str(input.get("Decision")) == util.cfgValue(config, "DecisionApprove")
    Map<String, Object> refund = refundCalc(policy, cancellationDate(endorsement))
    String status
    String endorsementNo = requestNo
    if (approve) {
        // the saved request only holds the cancellation terms, so it is replaced by a fresh endorsement with the same terms that is processed in one go;
        // when the platform refuses, that fresh endorsement stays pending as the new request
        suspend(endorsement)
        boolean freeLook = util.str(endorsement.get("CancelType")) == util.cfgValue(config, "CancelTypeFreeLook")
        Map<String, Object> created = createRequest(policy, util.str(endorsement.get("EndoEffectiveDate")).take(10), freeLook, util.str(endorsement.get("OtherCancelReason")))
        Map<String, Object> calculated = client.call("POST", endoBase + "/calculateEx", created)
        boolean ok = calculated.get("status") == 200
        Map<String, Object> calcBody = ok ? client.parse(calculated) : new HashMap<String, Object>()
        if (ok) {
            Map<String, Object> validated = client.call("POST", endoBase + "/validate", calcBody)
            ok = validated.get("status") == 200 || validated.get("status") == 204
        }
        if (ok) {
            Map<String, Object> issued = client.call("POST", endoBase + "/issueEndorsement", calcBody)
            ok = issued.get("status") == 200
        }
        if (!ok) {
            String detail = util.str(calculated.get("body")).take(Integer.parseInt(util.cfgValue(config, "PlatformErrorMaxLength")))
            throw new IllegalArgumentException("CONFLICT:The platform refused the cancellation of ${policyNo}; the request is still pending as ${util.str(created.get('EndoNo'))}. ${detail}".toString())
        }
        endorsementNo = util.str(created.get("EndoNo"))
        status = util.cfgValue(config, "RequestStatusApproved")
        policy = (Map<String, Object>) proposalSdkClient.proposalApi().newLoadRequestBuilder().policyNo(policyNo).withCodeDesc(util.yes()).doRequest().getBody()
    } else {
        suspend(endorsement)
        status = util.cfgValue(config, "RequestStatusRejected")
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("RequestNo", requestNo)
    out.put("RequestStatus", status)
    out.put("EndorsementNo", endorsementNo)
    out.put("PolicyInfo", policyInfo(policy))
    ((UPProductData) getCommonService("UPProductData")).addCarrier(out, util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    out.put("PolicyStatus", policyStatus(policy))
    out.put("RefundPremium", approve ? refund.get("RefundPremium") : null)
    UPNotify notifier = (UPNotify) getCommonService("UPNotify")
    Map<String, String> extra = new HashMap<String, String>()
    extra.put("RequestNo", requestNo)
    extra.put("Refund", util.fmtMoney(refund.get("RefundPremium")))
    Map<String, String> params = notifier.paramsOf(policy, extra)
    out.put("Notifications", notifier.fire(approve ? "CANCEL_APPROVED" : "CANCEL_REJECTED", params, customer, requesterId, ""))
    return out
}

/**
 * Refund rule for a cancellation: full premium within the free-look period (counted from the commencement date),
 * otherwise the percentage configured in UP_ProductRule (ProRataRefundPercent) of the pro-rata premium. Premium = plan premium on the risk
 * (before tax). FreeLookDays and ProRataRefundPercent come from ProductRule.
 */
Map<String, Object> refundCalc(Map<String, Object> policy, java.time.LocalDate cancelDate) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    UPProductData products = (UPProductData) getCommonService("UPProductData")
    Map<String, Object> lob = (Map<String, Object>) ((List) policy.get("PolicyLobList")).get(0)
    Map<String, Object> risk = (Map<String, Object>) ((List) lob.get("PolicyRiskList")).get(0)
    Map<String, Object> rule = products.getRule(util.str(policy.get("ProductCode")), util.str(policy.get("ProductSubcode")))
    if (!util.str(rule.get("FreeLookDays")) || !util.str(rule.get("ProRataRefundPercent"))) {
        throw new IllegalStateException("FreeLookDays / ProRataRefundPercent are not configured in UP_ProductRule for " + util.str(policy.get("ProductCode")))
    }
    int freeLookDays = Integer.parseInt(util.str(rule.get("FreeLookDays")))
    BigDecimal percent = new BigDecimal(util.str(rule.get("ProRataRefundPercent")))
    java.time.LocalDate start = java.time.LocalDate.parse(util.str(policy.get("EffectiveDate")).substring(0, 10))
    java.time.LocalDate end = java.time.LocalDate.parse(util.str(policy.get("ExpiryDate")).substring(0, 10))
    if (cancelDate.isBefore(start)) {
        util.fail("CancellationDate ${cancelDate} is before the commencement date ${start}".toString())
    }
    if (cancelDate.isAfter(end)) {
        util.fail("CancellationDate ${cancelDate} is after the expiry date ${end}".toString())
    }
    BigDecimal premium = util.toDecimal(risk.get("DuePremium"))
    long totalDays = ChronoUnit.DAYS.between(start, end) + 1
    long elapsed = ChronoUnit.DAYS.between(start, cancelDate)
    long remaining = totalDays - elapsed
    boolean freeLook = elapsed <= freeLookDays
    Map<String, String> config = util.configMap("*")
    int scale = util.moneyScale()
    java.math.RoundingMode rounding = util.roundingMode()
    BigDecimal base = util.percentBase()
    BigDecimal proRata = premium.multiply(new BigDecimal(remaining)).divide(new BigDecimal(totalDays), scale, rounding)
    BigDecimal refund = freeLook ? premium.setScale(scale, rounding)
            : proRata.multiply(percent).divide(base, scale, rounding)
    Map<String, Object> r = new LinkedHashMap<String, Object>()
    r.put("CancellationType", freeLook ? util.cfgValue(config, "RefundTypeFreeLook") : util.cfgValue(config, "RefundTypeProRata"))
    r.put("Premium", premium.setScale(scale, rounding))
    r.put("FreeLookDays", freeLookDays)
    r.put("DaysSinceCommencement", elapsed)
    r.put("PolicyPeriodDays", totalDays)
    r.put("UnexpiredDays", remaining)
    r.put("ProRataPremium", proRata)
    r.put("RefundPercent", freeLook ? base : percent)
    r.put("RefundPremium", refund)
    return r
}
