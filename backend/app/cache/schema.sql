CREATE TABLE IF NOT EXISTS events (
  _id              VARCHAR PRIMARY KEY,
  time             TIMESTAMP,
  hostname         VARCHAR,
  fqdn             VARCHAR,
  region           VARCHAR,
  account_id       VARCHAR,
  provider         VARCHAR,
  resource_id      VARCHAR,
  vm_id            VARCHAR,
  cluster          VARCHAR,
  namespace        VARCHAR,
  collections      VARCHAR[],
  version          VARCHAR,
  is_container     BOOLEAN,
  container_id     VARCHAR,
  container_name   VARCHAR,
  image_name       VARCHAR,
  image_id         VARCHAR,
  profile_id       VARCHAR,
  label            VARCHAR,
  labels_json      JSON,
  type             VARCHAR,
  attack_type      VARCHAR,
  attack_techniques VARCHAR[],
  effect           VARCHAR,
  severity         VARCHAR,
  count            INTEGER,
  rule_name        VARCHAR,
  msg              VARCHAR,
  err              VARCHAR,
  interactive      BOOLEAN,
  user_name        VARCHAR,
  pid              INTEGER,
  process_path     VARCHAR,
  command          VARCHAR,
  filepath         VARCHAR,
  md5              VARCHAR,
  ip               VARCHAR,
  port             INTEGER,
  country          VARCHAR,
  domain           VARCHAR,
  app              VARCHAR,
  app_id           VARCHAR,
  function_name    VARCHAR,
  function_id      VARCHAR,
  request_id       VARCHAR,
  runtime          VARCHAR,
  os               VARCHAR,
  wildfire_url     VARCHAR,
  raw              JSON
);

CREATE INDEX IF NOT EXISTS idx_time      ON events(time);
CREATE INDEX IF NOT EXISTS idx_type      ON events(type);
CREATE INDEX IF NOT EXISTS idx_effect    ON events(effect);
CREATE INDEX IF NOT EXISTS idx_severity  ON events(severity);
CREATE INDEX IF NOT EXISTS idx_namespace ON events(namespace);
CREATE INDEX IF NOT EXISTS idx_cluster   ON events(cluster);
CREATE INDEX IF NOT EXISTS idx_image     ON events(image_name);
CREATE INDEX IF NOT EXISTS idx_hostname  ON events(hostname);
CREATE INDEX IF NOT EXISTS idx_rule      ON events(rule_name);
CREATE INDEX IF NOT EXISTS idx_attack    ON events(attack_type);
