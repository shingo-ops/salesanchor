package jp.salesanchor.lineexport;

import android.app.Activity;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

/**
 * PINを一度だけ入力してアプリ私有領域(PinStore)に保存するだけの設定画面。
 * PINの平文は画面に表示しない（EditTextはnumberPasswordでマスク、保存後は
 * 「保存済み/未設定」のステータスのみ表示）。
 */
public class SettingsActivity extends Activity {

    private TextView statusText;
    private EditText pinInput;
    private View inputSection;

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

        refreshStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshStatus();
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
    }
}
