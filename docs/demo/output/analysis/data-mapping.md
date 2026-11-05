# Data mapping drafts (copybook → DB2 / Java)

Mechanical first draft. Column names drop the common field prefix; types come from the PIC clause.
Review every REDEFINES / OCCURS / FILLER / date field. Rules: `references/data-vsam-db2.md`.

## COCOM01Y  
Source: [cpy/COCOM01Y.cpy](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cpy/COCOM01Y.cpy)

| Legacy field | PIC / usage | Target column | DB2 type | Java field | Java type | Note |
|---|---|---|---|---|---|---|
| CDEMO-FROM-TRANID | X(04)  | FROM_TRANID | CHAR(4) | fromTranid | String |  |
| CDEMO-FROM-PROGRAM | X(08)  | FROM_PROGRAM | CHAR(8) | fromProgram | String |  |
| CDEMO-TO-TRANID | X(04)  | TO_TRANID | CHAR(4) | toTranid | String |  |
| CDEMO-TO-PROGRAM | X(08)  | TO_PROGRAM | CHAR(8) | toProgram | String |  |
| CDEMO-USER-ID | X(08)  | USER_ID | CHAR(8) | userId | String |  |
| CDEMO-USER-TYPE | X(01)  | USER_TYPE | CHAR(1) | userType | String |  |
| CDEMO-PGM-CONTEXT | 9(01) DISPLAY | PGM_CONTEXT | INTEGER | pgmContext | int |  |
| CDEMO-CUST-ID | 9(09) DISPLAY | CUST_ID | INTEGER | custId | int |  |
| CDEMO-CUST-FNAME | X(25)  | CUST_FNAME | VARCHAR(25) | custFname | String |  |
| CDEMO-CUST-MNAME | X(25)  | CUST_MNAME | VARCHAR(25) | custMname | String |  |
| CDEMO-CUST-LNAME | X(25)  | CUST_LNAME | VARCHAR(25) | custLname | String |  |
| CDEMO-ACCT-ID | 9(11) DISPLAY | ACCT_ID | BIGINT | acctId | long |  |
| CDEMO-ACCT-STATUS | X(01)  | ACCT_STATUS | CHAR(1) | acctStatus | String |  |
| CDEMO-CARD-NUM | 9(16) DISPLAY | CARD_NUM | BIGINT | cardNum | long |  |
| CDEMO-LAST-MAP | X(7)  | LAST_MAP | CHAR(7) | lastMap | String |  |
| CDEMO-LAST-MAPSET | X(7)  | LAST_MAPSET | CHAR(7) | lastMapset | String |  |

```sql
-- draft: name the table, set NOT NULL and the PRIMARY KEY from the VSAM key / business key
CREATE TABLE COCOM01Y (
  FROM_TRANID                    CHAR(4),
  FROM_PROGRAM                   CHAR(8),
  TO_TRANID                      CHAR(4),
  TO_PROGRAM                     CHAR(8),
  USER_ID                        CHAR(8),
  USER_TYPE                      CHAR(1),
  PGM_CONTEXT                    INTEGER,
  CUST_ID                        INTEGER,
  CUST_FNAME                     VARCHAR(25),
  CUST_MNAME                     VARCHAR(25),
  CUST_LNAME                     VARCHAR(25),
  ACCT_ID                        BIGINT,
  ACCT_STATUS                    CHAR(1),
  CARD_NUM                       BIGINT,
  LAST_MAP                       CHAR(7),
  LAST_MAPSET                    CHAR(7)
);
```

## COTTL01Y  
Source: [cpy/COTTL01Y.cpy](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cpy/COTTL01Y.cpy)

| Legacy field | PIC / usage | Target column | DB2 type | Java field | Java type | Note |
|---|---|---|---|---|---|---|
| CCDA-TITLE01 | X(40)  | TITLE01 | VARCHAR(40) | title01 | String |  |
| CCDA-TITLE02 | X(40)  | TITLE02 | VARCHAR(40) | title02 | String |  |
| CCDA-THANK-YOU | X(40)  | THANK_YOU | VARCHAR(40) | thankYou | String |  |

```sql
-- draft: name the table, set NOT NULL and the PRIMARY KEY from the VSAM key / business key
CREATE TABLE COTTL01Y (
  TITLE01                        VARCHAR(40),
  TITLE02                        VARCHAR(40),
  THANK_YOU                      VARCHAR(40)
);
```

## CSDAT01Y  
Source: [cpy/CSDAT01Y.cpy](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cpy/CSDAT01Y.cpy)

| Legacy field | PIC / usage | Target column | DB2 type | Java field | Java type | Note |
|---|---|---|---|---|---|---|
| WS-CURDATE-YEAR | 9(04) DISPLAY | CURDATE_YEAR | INTEGER | curdateYear | int | date: confirm format → DATE |
| WS-CURDATE-MONTH | 9(02) DISPLAY | CURDATE_MONTH | INTEGER | curdateMonth | int | date: confirm format → DATE |
| WS-CURDATE-DAY | 9(02) DISPLAY | CURDATE_DAY | INTEGER | curdateDay | int | date: confirm format → DATE |
| WS-CURDATE-N | 9(08) DISPLAY | CURDATE_N | INTEGER | curdateN | int | REDEFINES WS-CURDATE: variant layout, decide discriminator; date: confirm format → DATE |
| WS-CURTIME-HOURS | 9(02) DISPLAY | CURTIME_HOURS | INTEGER | curtimeHours | int |  |
| WS-CURTIME-MINUTE | 9(02) DISPLAY | CURTIME_MINUTE | INTEGER | curtimeMinute | int |  |
| WS-CURTIME-SECOND | 9(02) DISPLAY | CURTIME_SECOND | INTEGER | curtimeSecond | int |  |
| WS-CURTIME-MILSEC | 9(02) DISPLAY | CURTIME_MILSEC | INTEGER | curtimeMilsec | int |  |
| WS-CURTIME-N | 9(08) DISPLAY | CURTIME_N | INTEGER | curtimeN | int | REDEFINES WS-CURTIME: variant layout, decide discriminator |
| WS-CURDATE-MM | 9(02) DISPLAY | CURDATE_MM | INTEGER | curdateMm | int | date: confirm format → DATE |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-CURDATE-DD | 9(02) DISPLAY | CURDATE_DD | INTEGER | curdateDd | int | date: confirm format → DATE |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-CURDATE-YY | 9(02) DISPLAY | CURDATE_YY | INTEGER | curdateYy | int | date: confirm format → DATE |
| WS-CURTIME-HH | 9(02) DISPLAY | CURTIME_HH | INTEGER | curtimeHh | int |  |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-CURTIME-MM | 9(02) DISPLAY | CURTIME_MM | INTEGER | curtimeMm | int |  |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-CURTIME-SS | 9(02) DISPLAY | CURTIME_SS | INTEGER | curtimeSs | int |  |
| WS-TIMESTAMP-DT-YYYY | 9(04) DISPLAY | TIMESTAMP_DT_YYYY | INTEGER | timestampDtYyyy | int | date: confirm format → DATE |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-TIMESTAMP-DT-MM | 9(02) DISPLAY | TIMESTAMP_DT_MM | INTEGER | timestampDtMm | int | date: confirm format → DATE |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-TIMESTAMP-DT-DD | 9(02) DISPLAY | TIMESTAMP_DT_DD | INTEGER | timestampDtDd | int | date: confirm format → DATE |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-TIMESTAMP-TM-HH | 9(02) DISPLAY | TIMESTAMP_TM_HH | INTEGER | timestampTmHh | int |  |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-TIMESTAMP-TM-MM | 9(02) DISPLAY | TIMESTAMP_TM_MM | INTEGER | timestampTmMm | int |  |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-TIMESTAMP-TM-SS | 9(02) DISPLAY | TIMESTAMP_TM_SS | INTEGER | timestampTmSs | int |  |
| FILLER | X(01) | — | — | — | — | unused bytes: confirm and drop |
| WS-TIMESTAMP-TM-MS6 | 9(06) DISPLAY | TIMESTAMP_TM_MS6 | INTEGER | timestampTmMs6 | int |  |

```sql
-- draft: name the table, set NOT NULL and the PRIMARY KEY from the VSAM key / business key
CREATE TABLE CSDAT01Y (
  CURDATE_YEAR                   INTEGER,
  CURDATE_MONTH                  INTEGER,
  CURDATE_DAY                    INTEGER,
  CURTIME_HOURS                  INTEGER,
  CURTIME_MINUTE                 INTEGER,
  CURTIME_SECOND                 INTEGER,
  CURTIME_MILSEC                 INTEGER,
  CURDATE_MM                     INTEGER,
  CURDATE_DD                     INTEGER,
  CURDATE_YY                     INTEGER,
  CURTIME_HH                     INTEGER,
  CURTIME_MM                     INTEGER,
  CURTIME_SS                     INTEGER,
  TIMESTAMP_DT_YYYY              INTEGER,
  TIMESTAMP_DT_MM                INTEGER,
  TIMESTAMP_DT_DD                INTEGER,
  TIMESTAMP_TM_HH                INTEGER,
  TIMESTAMP_TM_MM                INTEGER,
  TIMESTAMP_TM_SS                INTEGER,
  TIMESTAMP_TM_MS6               INTEGER
);
```

## CSMSG01Y  
Source: [cpy/CSMSG01Y.cpy](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cpy/CSMSG01Y.cpy)

| Legacy field | PIC / usage | Target column | DB2 type | Java field | Java type | Note |
|---|---|---|---|---|---|---|
| CCDA-MSG-THANK-YOU | X(50)  | MSG_THANK_YOU | VARCHAR(50) | msgThankYou | String |  |
| CCDA-MSG-INVALID-KEY | X(50)  | MSG_INVALID_KEY | VARCHAR(50) | msgInvalidKey | String |  |

```sql
-- draft: name the table, set NOT NULL and the PRIMARY KEY from the VSAM key / business key
CREATE TABLE CSMSG01Y (
  MSG_THANK_YOU                  VARCHAR(50),
  MSG_INVALID_KEY                VARCHAR(50)
);
```

## CSUSR01Y  
Source: [cpy/CSUSR01Y.cpy](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cpy/CSUSR01Y.cpy)

| Legacy field | PIC / usage | Target column | DB2 type | Java field | Java type | Note |
|---|---|---|---|---|---|---|
| SEC-USR-ID | X(08)  | USR_ID | CHAR(8) | usrId | String |  |
| SEC-USR-FNAME | X(20)  | USR_FNAME | VARCHAR(20) | usrFname | String |  |
| SEC-USR-LNAME | X(20)  | USR_LNAME | VARCHAR(20) | usrLname | String |  |
| SEC-USR-PWD | X(08)  | USR_PWD | CHAR(8) | usrPwd | String |  |
| SEC-USR-TYPE | X(01)  | USR_TYPE | CHAR(1) | usrType | String |  |
| SEC-USR-FILLER | X(23)  | USR_FILLER | VARCHAR(23) | usrFiller | String |  |

```sql
-- draft: name the table, set NOT NULL and the PRIMARY KEY from the VSAM key / business key
CREATE TABLE CSUSR01Y (
  USR_ID                         CHAR(8),
  USR_FNAME                      VARCHAR(20),
  USR_LNAME                      VARCHAR(20),
  USR_PWD                        CHAR(8),
  USR_TYPE                       CHAR(1),
  USR_FILLER                     VARCHAR(23)
);
```

