CREATE TABLE amis (
    title text,
    example text,
    en text,
    cmn text);
CREATE INDEX amis_title ON amis (title);
CREATE TABLE fuzzy (fuzz text, amis text);
CREATE INDEX fuzzy_fuzz on fuzzy (fuzz);
