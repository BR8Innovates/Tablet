#!/usr/bin/env python3
"""Maker / Checker workflow set-up: creates UP_UserRole and UP_NotifyTemplate and the config keys / field rules the new APIs need.
Idempotent for tables; row Ids are fixed (UP_FieldRule from 139, UP_ApiConfig from 82). Re-running on existing Ids is refused by the platform (insert-only), so run once."""
import sys, json
sys.path.insert(0, ".")
from uptab import *
FR = 1188575333; CFG = 1188575596
users = table("UP_UserRole", [("UserRoleKey", S), ("UserName", S), ("UserId", S), ("Role", S), ("DisplayName", S), ("Branch", S), ("Email", S), ("Mobile", S), ("IsActive", S)])
print("UP_UserRole", users)
U = "ravi.teja@insuremo.com"
save("UP_UserRole", users, [dict(UserRoleKey=f"{U}|{r}", UserName=U, UserId="1188178494", Role=r, DisplayName="Ravi Teja (test user - replace with bank staff)", Branch="001", Email=U, IsActive="Y")
                            for r in ("MAKER", "PROPOSAL_CHECKER", "CANCELLATION_CHECKER")], 1, "userrole")
tpl = table("UP_NotifyTemplate", [("TemplateKey", S), ("Event", S), ("Recipient", S), ("Channel", S), ("Subject", S), ("Body", S), ("SmsTemplateCode", S), ("IsActive", S)])
print("UP_NotifyTemplate", tpl)
T = []
def add(event, rcpt, subject, email_body, sms_body):
    T.append(dict(TemplateKey=f"{event}|{rcpt}|EMAIL", Event=event, Recipient=rcpt, Channel="EMAIL", Subject=subject, Body=email_body, SmsTemplateCode="NONE", IsActive="Y"))
    T.append(dict(TemplateKey=f"{event}|{rcpt}|SMS", Event=event, Recipient=rcpt, Channel="SMS", Subject="-", Body=sms_body, SmsTemplateCode="NONE", IsActive="Y"))
add("SUBMITTED", "PROPOSAL_CHECKER", "Proposal {ProposalNo} waiting for approval", "A proposal has been submitted by {Maker} and is waiting for your approval.\n\nProposal: {ProposalNo}\nProduct: {Product}\nPlan: {Plan}\nInsured: {Insured}\nPremium: {Premium}\n\nOpen the portal: {Link}", "Proposal {ProposalNo} ({Product}, {Insured}) submitted by {Maker} awaits your approval. {Link}")
add("PROPOSAL_ISSUED", "MAKER", "Proposal {ProposalNo} approved - policy {PolicyNo}", "Your proposal {ProposalNo} was approved by {Checker}.\n\nPolicy number: {PolicyNo}\nInsured: {Insured}\nProduct: {Product}", "Proposal {ProposalNo} approved. Policy {PolicyNo} issued.")
add("PROPOSAL_ISSUED", "CUSTOMER", "Your {Insurer} policy {PolicyNo}", "Dear {Insured},\n\nYour policy has been issued.\n\nPolicy number: {PolicyNo}\nProduct: {Product}\nPlan: {Plan}\nPremium: {Premium}\nInsurer: {Insurer}\n\nThank you for choosing Sohar International Bank.", "Dear {Insured}, your {Insurer} policy {PolicyNo} ({Product}) has been issued. Sohar International Bank")
add("PROPOSAL_REJECTED", "MAKER", "Proposal {ProposalNo} rejected", "Your proposal {ProposalNo} was rejected by {Checker}.\n\nReason: {Reason}\nInsured: {Insured}\nProduct: {Product}", "Proposal {ProposalNo} rejected by {Checker}. Reason: {Reason}")
add("CANCEL_REQUESTED", "CANCELLATION_CHECKER", "Cancellation request {RequestNo} for policy {PolicyNo}", "{Maker} has requested the cancellation of policy {PolicyNo}.\n\nRequest: {RequestNo}\nInsured: {Insured}\nReason: {Reason}\nRefund: {Refund}\n\nOpen the portal: {Link}", "Cancellation request {RequestNo} for policy {PolicyNo} by {Maker}. Refund {Refund}. {Link}")
add("CANCEL_APPROVED", "MAKER", "Cancellation of policy {PolicyNo} approved", "The cancellation of policy {PolicyNo} was approved by {Checker}.\n\nRefund: {Refund}", "Cancellation of policy {PolicyNo} approved. Refund {Refund}.")
add("CANCEL_APPROVED", "CUSTOMER", "Your policy {PolicyNo} has been cancelled", "Dear {Insured},\n\nYour policy {PolicyNo} ({Product}) has been cancelled as requested.\nRefund amount: {Refund}\n\nSohar International Bank", "Dear {Insured}, policy {PolicyNo} is cancelled. Refund {Refund}. Sohar International Bank")
add("CANCEL_REJECTED", "MAKER", "Cancellation request {RequestNo} rejected", "The cancellation request {RequestNo} for policy {PolicyNo} was rejected by {Checker}.", "Cancellation request {RequestNo} for policy {PolicyNo} rejected by {Checker}.")
add("SHARE_QUOTATION", "CUSTOMER", "Your insurance quotation from {Insurer}", "Dear {Insured},\n\nPlease find your quotation.\n\nProduct: {Product}\nPlan: {Plan}\nPremium: {Premium}\nCover from: {EffectiveDate}\nInsurer: {Insurer}\n\nSohar International Bank", "Dear {Insured}, quotation: {Product} {Plan}, premium {Premium}. {Insurer}. Sohar International Bank")
add("SHARE_PROPOSAL", "CUSTOMER", "Your proposal {ProposalNo}", "Dear {Insured},\n\nYour proposal {ProposalNo} for {Product} ({Plan}) has been recorded.\nPremium: {Premium}\nInsurer: {Insurer}\n\nSohar International Bank", "Dear {Insured}, proposal {ProposalNo} ({Product}) recorded. Premium {Premium}. Sohar International Bank")
add("SHARE_POLICY", "CUSTOMER", "Your policy {PolicyNo}", "Dear {Insured},\n\nYour policy {PolicyNo} for {Product} ({Plan}) is effective from {EffectiveDate}.\nPremium: {Premium}\nInsurer: {Insurer}\n\nSohar International Bank", "Dear {Insured}, policy {PolicyNo} ({Product}) effective {EffectiveDate}. Sohar International Bank")
save("UP_NotifyTemplate", tpl, T, 1, "notifytpl")
# configuration keys (no literals in code)
K = [("RoleEnforcement", "N"), ("AllowSelfApproval", "N"), ("NotifyMode", "DRYRUN"), ("EmailAccountName", "NONE"), ("SmsAccountName", "NONE"),
     ("PortalUrl", "https://portal.insuremo.com/uic-web/#/p/sohar-insurance-portal"), ("DashboardMaxDays", "180"), ("WorklistPageSize", "20"), ("WorklistMaxRows", "1000"),
     ("SearchPath", "/platform/proposal/v1/queryPolicy"), ("EndoSearchPath", "/platform/endo/v1/query"),
     ("ProposalStatusPending", "2"), ("ProposalStatusIssued", "3"), ("ProposalStatusRejected", "4"),
     ("EndoStatusPending", "120"), ("EndoStatusIssued", "300"), ("EndoStatusWithdrawn", "600"),
     ("RoleMaker", "MAKER"), ("RoleProposalChecker", "PROPOSAL_CHECKER"), ("RoleCancellationChecker", "CANCELLATION_CHECKER"),
     ("ShareDocQuotation", "SHARE_QUOTATION"), ("ShareDocProposal", "SHARE_PROPOSAL"), ("ShareDocPolicy", "SHARE_POLICY")]
save("UP_ApiConfig", CFG, [dict(Api="*", Scope="*", Key=k, Value=v) for k, v in K], 82, "wfcfg")
rules = []
def R(api, path, label, req, typ="string", **kw):
    d = dict(Api=api, Path=path, Label=label, Required=req, DataType=typ, AppliesTo="*"); d.update(kw); rules.append(d)
CH = dict(MinLength=2, MaxLength=20, Pattern="^[A-Z0-9_]+$", CodeTable="UP_Channel", CodeColumn="ChannelCode")
DT = dict(Pattern="^\\d{4}-\\d{2}-\\d{2}$")
for api in ("UPWorklist", "UPDashboard", "UPShare", "UPCancelDetail"):
    R(api, "ChannelCode", "Channel code", "Y", **CH)
R("UPWorklist", "Type", "Worklist type", "Y", "enum", EnumValues="PROPOSAL,CANCELLATION,MINE")
R("UPWorklist", "Status", "Status filter", "N", "enum", EnumValues="PENDING,ISSUED,REJECTED,ALL")
R("UPWorklist", "FromDate", "From date", "N", "date", **DT); R("UPWorklist", "ToDate", "To date", "N", "date", **DT)
R("UPWorklist", "PageNo", "Page number", "N", "integer", MinValue=1, MaxValue=1000); R("UPWorklist", "PageSize", "Page size", "N", "integer", MinValue=1, MaxValue=100)
R("UPWorklist", "ProductCode", "Product code", "N", MinLength=3, MaxLength=10, Pattern="^[A-Z0-9]+$")
R("UPDashboard", "FromDate", "From date", "N", "date", **DT); R("UPDashboard", "ToDate", "To date", "N", "date", **DT)
R("UPShare", "DocType", "Document type", "Y", "enum", EnumValues="QUOTATION,PROPOSAL,POLICY")
R("UPShare", "Channel", "Delivery channel", "Y", "enum", EnumValues="EMAIL,SMS,BOTH")
R("UPShare", "Email", "Email address", "N", MinLength=5, MaxLength=80, Pattern="^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")
R("UPShare", "Mobile", "Mobile number", "N", MinLength=7, MaxLength=15, Pattern="^\\+?[0-9]{7,15}$")
R("UPShare", "ProposalNo", "Proposal number", "N", MinLength=5, MaxLength=30, Pattern="^[A-Za-z0-9/_-]+$")
R("UPShare", "PolicyNo", "Policy number", "N", MinLength=5, MaxLength=30, Pattern="^[A-Za-z0-9/_-]+$")
R("UPCancelDetail", "PolicyNo", "Policy number", "N", MinLength=5, MaxLength=30, Pattern="^[A-Za-z0-9/_-]+$")
R("UPCancelDetail", "ProposalNo", "Proposal number", "N", MinLength=5, MaxLength=30, Pattern="^[A-Za-z0-9/_-]+$")
save("UP_FieldRule", FR, rules, 139, "wfrule")
print("rules", len(rules), "keys", len(K), "templates", len(T))
