-- Planned PostgreSQL integration contract; NOT executed by this fixture.
CREATE TABLE return_event (tenant text NOT NULL, token text NOT NULL, loan text NOT NULL, equipment text NOT NULL, damaged boolean NOT NULL, result text NOT NULL, PRIMARY KEY(tenant,token));
CREATE TABLE cleaning_task (loan text PRIMARY KEY);
-- Loan update, event insert and cleaning insert must share one DB transaction.
