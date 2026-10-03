import sys; sys.path.insert(0, ".")
from uptab import *
CFG = 1188575596
K = [("EndoSearchModule", "Endorsement"), ("DashboardMaxPolicies", "60"), ("EndoTypeCancelFilter", "3"), ("CancelFreeLookLabel", "Free look")]
save("UP_ApiConfig", CFG, [dict(Api="*", Scope="*", Key=k, Value=v) for k, v in K], 109, "wfcfg3")
