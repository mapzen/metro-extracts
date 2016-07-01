DROP TABLE IF EXISTS extracts;

CREATE TABLE extracts (

    -- Hard-to-guess string for public link us.
    id              VARCHAR(64) PRIMARY KEY,
    
    -- Information for pre-extract request.
    envelope_id     VARCHAR(64) NOT NULL,
    envelope_bbox   FLOAT[],
    
    -- ODES service identifier for extract.
    odes_id         INTEGER NULL,

    -- Who and when.
    user_id         INTEGER NOT NULL,
    created         TIMESTAMP NOT NULL,
    
    -- Where does this extract cover?
    wof_name        TEXT NULL,
    wof_id          INTEGER NULL

);
