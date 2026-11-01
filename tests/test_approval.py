from approval import issue_token, verify_token

def test_valid_token_is_action_bound():
    token = issue_token("INC001245", "add_work_note", "Investigate KE0042")
    assert verify_token(token, "INC001245", "add_work_note", "Investigate KE0042")
    assert not verify_token(token, "INC001246", "add_work_note", "Investigate KE0042")
    assert not verify_token(token, "INC001245", "set_status", "Investigate KE0042")
