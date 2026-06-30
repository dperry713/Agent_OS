using System;
using Microsoft.Data.Sqlite;
using System.IO;

namespace AgentOS.Frontend.Services
{
    public class SettingsService
    {
        private readonly string _dbPath;

        public SettingsService()
        {
            // Locate the database file relative to the application base directory.
            var appDir = AppContext.BaseDirectory;
            _dbPath = Path.Combine(appDir, "settings.db");
            EnsureDatabase();
        }

        private void EnsureDatabase()
        {
            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            conn.Open();
            var cmd = conn.CreateCommand();
            cmd.CommandText = @"CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);";
            cmd.ExecuteNonQuery();
        }

        public bool GetDarkThemeEnabled()
        {
            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            conn.Open();
            var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT value FROM settings WHERE key = 'dark_theme';";
            var result = cmd.ExecuteScalar() as string;
            return result == "1";
        }

        public void SetDarkThemeEnabled(bool enabled)
        {
            using var conn = new SqliteConnection($"Data Source={_dbPath}");
            conn.Open();
            var cmd = conn.CreateCommand();
            cmd.CommandText = @"INSERT INTO settings(key, value) VALUES('dark_theme', @val)
                                ON CONFLICT(key) DO UPDATE SET value = @val;";
            cmd.Parameters.AddWithValue("@val", enabled ? "1" : "0");
            cmd.ExecuteNonQuery();
        }
    }
}
