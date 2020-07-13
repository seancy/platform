CREATE ALGORITHM=UNDEFINED DEFINER=`learning-customer2_admin`@`%` SQL SECURITY DEFINER VIEW `triboo_analytics_leaderboardview` AS
  SELECT
    `triboo_analytics_leaderboard`.`id` AS `id`,
    `triboo_analytics_leaderboard`.`user_id` AS `user_id`,
    `triboo_analytics_leaderboard_total`.`total_score` AS `total_score`,
    (`triboo_analytics_leaderboard_total`.`total_score` - `triboo_analytics_leaderboard`.`last_week_score`) AS `current_week_score`,
    (`triboo_analytics_leaderboard_total`.`total_score` - `triboo_analytics_leaderboard`.`last_month_score`) AS `current_month_score`,
    `triboo_analytics_leaderboard`.`last_week_rank` AS `last_week_rank`,
    `triboo_analytics_leaderboard`.`last_month_rank` AS `last_month_rank`,
    `triboo_analytics_leaderboard`.`modified` AS `last_updated`
  FROM
    (`triboo_analytics_leaderboard` JOIN `triboo_analytics_leaderboard_total`)
  WHERE
    (`triboo_analytics_leaderboard`.`user_id` = `triboo_analytics_leaderboard_total`.`user_id`)
  ORDER BY
    `triboo_analytics_leaderboard_total`.`total_score` DESC;