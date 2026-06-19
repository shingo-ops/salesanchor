import type { ReactNode } from 'react';

export interface SplashScreenProps {
  /** Brand mark, e.g. <img src={favicon} alt="" />. */
  logo?: ReactNode;
}

/**
 * Full-screen boot loader: anchor mark blinks above three bouncing dots.
 * Render at the app root while initial data/auth resolves, then swap to <App/>.
 *   {!appReady ? <SplashScreen logo={<img src={favicon} alt="" />} /> : <App />}
 */
export function SplashScreen({ logo }: SplashScreenProps) {
  return (
    <div className="sa-splash" role="status" aria-label="Loading">
      <div className="sa-splash__mark">{logo}</div>
      <div className="sa-splash__dots">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
