import sys; sys.path.insert(0, ".")
from uptab import *
CFG = 1188575596
K = [("MsgForbidden", "You do not have the role required for this action."), ("MsgSelfApproval", "The person who created an item cannot approve or reject it."),
     ("MsgNotifyDryRun", "Notification recorded (dry run, nothing was sent)."), ("ShareMaxDetailLength", "80")]
save("UP_ApiConfig", CFG, [dict(Api="*", Scope="*", Key=k, Value=v) for k, v in K], 105, "wfcfg2")
