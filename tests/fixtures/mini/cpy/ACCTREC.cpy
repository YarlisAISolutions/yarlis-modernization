      * Synthetic account record.
       01  ACCOUNT-RECORD.
           05  ACCT-ID                PIC 9(11).
           05  ACCT-STATUS            PIC X(01).
               88  ACCT-ACTIVE        VALUE 'Y'.
               88  ACCT-CLOSED        VALUE 'N'.
           05  ACCT-CREDIT-LIMIT      PIC S9(10)V99 COMP-3.
           05  ACCT-OPEN-DATE         PIC X(10).
           05  FILLER                 PIC X(20).
