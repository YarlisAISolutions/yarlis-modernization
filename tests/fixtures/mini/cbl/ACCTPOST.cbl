      * Synthetic test program: batch posting to DB2.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCTPOST.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TRAN-FILE ASSIGN TO TRANIN.
       DATA DIVISION.
       FILE SECTION.
       FD  TRAN-FILE.
       01  TRAN-REC               PIC X(80).
       WORKING-STORAGE SECTION.
       01  WS-AMT                 PIC S9(9)V99 COMP-3.
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT TRAN-FILE
           READ TRAN-FILE
           EXEC SQL
              UPDATE ACCOUNT SET CURR_BAL = CURR_BAL + :WS-AMT
              WHERE ACCT_ID = 1
           END-EXEC
           CLOSE TRAN-FILE
           GOBACK.
