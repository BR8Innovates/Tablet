def code = Policy().ProductCode.val
def reason = Endorsement().CauseType.val
println(code)
println(reason)
def fee = 0
try {
	fee = lookup("Endor_AdminFee", ["ProductCode": code, "CancelReason": reason?.toString()]).AdminFee
	println(fee)
} catch (Exception e) {
	println("Endor_AdminFee lookup failed: " + e.getMessage())
	fee = 0
}
Endorsement().CancelFee.update(fee)
