use cms;
SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM login_users;
DELETE FROM org_ladder;

SET FOREIGN_KEY_CHECKS = 1;

<!-- here we are setting the two table login user and orgLaddr -->
## we atleast need this below seed in both the tables

## in orgLadder table add this row

'1', 'ORD', 'root', NULL
'2', '2_FOD', 'division', 1


## in loginUsers table add this row

'1', 'ORD', '123', 'super_admin', '1'
'2', '2_FOD', '123', 'scme', '2'
'3', 'ORD_BR', '123', 'ORD_BR', '2'

-- Or direct SQL INSERT statement:
-- INSERT INTO login_users (username, password, role, org_id) VALUES ('ORD_BR', '123', 'ORD_BR', 2);
