      * Synthetic test program: online account update (CICS).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCTUPD.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-MSG                 PIC X(40).
       01  WS-MENU-PGM            PIC X(8) VALUE 'MENU01'.
       01  WS-FILE                PIC X(8) VALUE 'ACCTDAT '.
       COPY ACCTREC.
       PROCEDURE DIVISION.
       MAIN-PARA.
           EXEC CICS RECEIVE MAP('ACCTUPA') MAPSET('ACCTUPD')
           END-EXEC
           PERFORM READ-ACCOUNT
           PERFORM UPDATE-ACCOUNT
           EXEC CICS RETURN TRANSID('AU01') END-EXEC.
       READ-ACCOUNT.
           EXEC CICS READ FILE(WS-FILE) INTO(ACCOUNT-RECORD)
                RIDFLD(ACCT-ID) UPDATE
           END-EXEC
           IF ACCT-ID = ZEROS
              MOVE 'Account not found, try again' TO WS-MSG
           END-IF.
       UPDATE-ACCOUNT.
           IF ACCT-CREDIT-LIMIT > 999999
              MOVE 'Credit limit is too high' TO WS-MSG
           ELSE
              EXEC CICS REWRITE FILE('ACCTDAT')
                   FROM(ACCOUNT-RECORD)
              END-EXEC
              EXEC CICS XCTL PROGRAM(WS-MENU-PGM) END-EXEC
           END-IF.
