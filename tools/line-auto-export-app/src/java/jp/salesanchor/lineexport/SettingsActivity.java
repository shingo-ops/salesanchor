package jp.salesanchor.lineexport;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.provider.Settings;
import android.text.TextUtils;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * 設定画面。PIN機能（保存済みかどうかだけ表示）に加え、LineNotifyListenerService
 * の状態表示・設定を持つ。通知の本文はここでは一切表示しない。
 */
public class SettingsActivity extends Activity {

    private static final int REQUEST_WRITE_EXTERNAL_STORAGE = 1001;

    private TextView statusText;
    private EditText pinInput;
    private View inputSection;

    private TextView notifyAccessStatusText;
    private TextView notifyCountText;
    private TextView notifyLastTimeText;
    private TextView notifyStoragePathText;
    private EditText notifyTargetGroupsInput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        statusText = (TextView) findViewById(R.id.status_text);
        pinInput = (EditText) findViewById(R.id.pin_input);
        inputSection = findViewById(R.id.input_section);
        Button saveButton = (Button) findViewById(R.id.save_button);

        saveButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                savePin();
            }
        });

        notifyAccessStatusText = (TextView) findViewById(R.id.notify_access_status_text);
        notifyCountText = (TextView) findViewById(R.id.notify_count_text);
        notifyLastTimeText = (TextView) findViewById(R.id.notify_last_time_text);
        notifyStoragePathText = (TextView) findViewById(R.id.notify_storage_path_text);
        notifyTargetGroupsInput = (EditText) findViewById(R.id.notify_target_groups_input);

        Button notifyOpenSettingsButton = (Button) findViewById(R.id.notify_open_settings_button);
        notifyOpenSettingsButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS"));
            }
        });

        Button notifyRequestStoragePermissionButton =
                (Button) findViewById(R.id.notify_request_storage_permission_button);
        notifyRequestStoragePermissionButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                requestPermissions(
                        new String[] {Manifest.permission.WRITE_EXTERNAL_STORAGE},
                        REQUEST_WRITE_EXTERNAL_STORAGE);
            }
        });

        Button notifyTargetGroupsSaveButton = (Button) findViewById(R.id.notify_target_groups_save_button);
        notifyTargetGroupsSaveButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                saveTargetGroups();
            }
        });

        refreshStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshStatus();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_WRITE_EXTERNAL_STORAGE) {
            boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            Toast.makeText(this, granted ? "許可されました" : "許可されませんでした", Toast.LENGTH_SHORT).show();
        }
    }

    private void saveTargetGroups() {
        String value = notifyTargetGroupsInput.getText().toString().trim();
        NotifyStore.setTargetGroups(this, value);
        Toast.makeText(this, R.string.notify_target_groups_saved, Toast.LENGTH_SHORT).show();
        refreshNotifyStatus();
    }

    /** 通知アクセスが有効かどうかを Settings.Secure から判定し、状態一式を再表示する。 */
    private void refreshNotifyStatus() {
        boolean enabled = isNotificationAccessEnabled();
        notifyAccessStatusText.setText(enabled
                ? R.string.notify_access_enabled
                : R.string.notify_access_disabled);

        long count = NotifyStore.getRecordCount(this);
        notifyCountText.setText(getString(R.string.notify_record_count_format, count));

        long lastTime = NotifyStore.getLastRecordTime(this);
        if (lastTime > 0) {
            String lastGroup = NotifyStore.getLastRecordGroup(this);
            String timeLabel = new SimpleDateFormat("yyyy/MM/dd HH:mm", Locale.JAPAN).format(new Date(lastTime));
            notifyLastTimeText.setText(getString(R.string.notify_last_time_format, timeLabel + " " + lastGroup));
        } else {
            notifyLastTimeText.setText(R.string.notify_last_time_none);
        }

        String storagePath = NotifyStore.getStoragePath(this);
        if (TextUtils.isEmpty(storagePath)) {
            notifyStoragePathText.setText(R.string.notify_storage_path_none);
        } else {
            notifyStoragePathText.setText(getString(R.string.notify_storage_path_format, storagePath));
        }

        if (!notifyTargetGroupsInput.isFocused()) {
            notifyTargetGroupsInput.setText(NotifyStore.getTargetGroups(this));
        }
    }

    private boolean isNotificationAccessEnabled() {
        String enabledListeners = Settings.Secure.getString(
                getContentResolver(), "enabled_notification_listeners");
        return enabledListeners != null && enabledListeners.contains(getPackageName());
    }

    private void savePin() {
        String pin = pinInput.getText().toString();
        pinInput.setText("");

        if (TextUtils.isEmpty(pin) || pin.length() < 4 || !pin.matches("\\d+")) {
            Toast.makeText(this, R.string.pin_invalid, Toast.LENGTH_SHORT).show();
            return;
        }

        PinStore.savePin(this, pin);
        refreshStatus();
        Toast.makeText(this, R.string.pin_saved, Toast.LENGTH_SHORT).show();
    }

    /** Shows only saved/unsaved status — never the PIN value itself. */
    private void refreshStatus() {
        boolean saved = PinStore.hasPin(this);
        statusText.setText(saved ? R.string.pin_status_saved : R.string.pin_status_unsaved);
        inputSection.setVisibility(saved ? View.GONE : View.VISIBLE);

        refreshNotifyStatus();
    }
}
