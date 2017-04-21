/* -------------- Collections list ---------------*/
coupon
members
sessions
system.indexes
system.users
user
wx_user

/* -------------- Indexes ---------------*/

db.user.ensureIndex({privilege:1})
db.user.ensureIndex({uname:1})
db.user.ensureIndex({login:1,privilege:1})

db.coupon.ensureIndex({state:1})
db.coupon.ensureIndex({code:1})
db.coupon.ensureIndex({member:1})

db.members.ensureIndex({member:1})
db.members.ensureIndex({code:1})
db.members.ensureIndex({status:1})

db.wx_user.ensureIndex({member:1})
db.wx_user.ensureIndex({wx_user:1})

db.sessions.ensureIndex({session_id:1})

