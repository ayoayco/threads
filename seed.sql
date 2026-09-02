-- The featured posts that used to live in `thread_ids` in threads.py.
-- Applied by `flask --app app.py init-db`; ignored if already present.
-- The site lists posts by their own date, so the order here does not matter.
INSERT OR IGNORE INTO statuses (status_id) VALUES
    ('113449531956042438'),
    ('113650907203476875'),
    ('114012659479108663'),
    ('114490408596372783'),
    ('114649657564007543'),
    ('116245553803866191'),
    ('116312536977108702'),
    ('116352859731078602'),
    ('116364343818471960'),
    ('116381905038904377'),
    ('116441682011075462'),
    ('116458548126648062'),
    ('116667802375475365');
