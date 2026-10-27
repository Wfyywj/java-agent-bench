-- Executed by Database.init in the actual H2 fixture (2.3.232).
CREATE TABLE batch(id INT PRIMARY KEY,status VARCHAR NOT NULL);
CREATE TABLE orders(id INT PRIMARY KEY,batch_id INT NOT NULL REFERENCES batch(id),status VARCHAR NOT NULL,quantity INT NOT NULL);
CREATE TABLE inventory(id INT PRIMARY KEY,available INT CHECK(available BETWEEN 0 AND 10));
-- Both shipping and cancellation first lock the same aggregate, not the whole table.
-- SELECT status FROM batch WHERE id=1 FOR UPDATE;
