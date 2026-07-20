import LegalPage from '../../components/chrome/LegalPage';

export const metadata = {
  title: 'Privacy Policy — VeilProof',
  description: 'How VeilProof collects, uses, and protects information when you use our invisible bot-detection services.',
};

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="July 20, 2026">
      <p>
        This Privacy Policy describes how VeilProof (&quot;VeilProof,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;)
        collects, uses, discloses, and protects information in connection with our websites,
        dashboards, APIs, SDKs, and related services (collectively, the &quot;Services&quot;).
      </p>
      <p>
        By accessing or using the Services, you acknowledge this Policy. If you do not agree,
        do not use the Services.
      </p>

      <h2>1. Who we are</h2>
      <p>
        VeilProof provides invisible, behavior-based bot detection and fraud-prevention tooling
        for websites and applications. Customers integrate our browser SDK and verify decisions
        server-side before trusting a request.
      </p>
      <h2>2. Information we collect</h2>
      <h3>2.1 Account and customer information</h3>
      <p>When you create an account or manage a project, we may collect:</p>
      <ul>
        <li>Name, email address, and authentication identifiers (including Google sign-in tokens where used)</li>
        <li>Project names, allowed domains, and API key metadata (hashed secrets; we do not store raw secret keys after display)</li>
        <li>Billing or commercial contact details if you purchase a paid plan (if offered)</li>
        <li>Support correspondence and feedback you send us</li>
      </ul>

      <h3>2.2 End-user / visitor signals (customer sites)</h3>
      <p>
        When a customer installs the VeilProof SDK on their site, the SDK may collect technical
        and behavioral signals needed to score bot risk, such as:
      </p>
      <ul>
        <li>Device and browser characteristics (for example user agent, platform, touch support, automation flags)</li>
        <li>Interaction telemetry (mouse, keyboard, scroll, focus, and related timing/path features)</li>
        <li>Session identifiers, timestamps, and derived risk scores / decisions</li>
        <li>Request metadata used for security (for example origin / domain checks)</li>
      </ul>
      <p>
        These signals are processed to provide bot detection to the customer. We do not use them
        to sell advertising profiles. Customers are responsible for providing appropriate notices
        to their own visitors where required by law.
      </p>

      <h3>2.3 Website and product analytics</h3>
      <p>
        On our marketing site and dashboards, we may collect standard log data (IP address,
        pages viewed, referrer, approximate location derived from IP) and product usage metrics
        to operate, secure, and improve the Services.
      </p>

      <h3>2.4 Cookies and similar technologies</h3>
      <p>
        We use cookies or local storage as needed for authentication, preference persistence,
        and essential product functions. You can control cookies through your browser settings;
        disabling some cookies may limit dashboard functionality.
      </p>

      <h2>3. How we use information</h2>
      <p>We use information to:</p>
      <ul>
        <li>Provide, operate, and maintain the Services (including risk scoring and siteverify)</li>
        <li>Authenticate users, manage API keys, and enforce domain / abuse controls</li>
        <li>Detect, prevent, and investigate fraud, abuse, and security incidents</li>
        <li>Improve models, reliability, and documentation (using aggregated or de-identified data where practical)</li>
        <li>Communicate service updates, security notices, and support responses</li>
        <li>Comply with law and enforce our Terms of Service</li>
      </ul>

      <h2>4. Legal bases (EEA/UK where applicable)</h2>
      <p>Where GDPR/UK GDPR applies, we process personal data on bases such as:</p>
      <ul>
        <li><strong>Contract</strong> — to provide the Services you request</li>
        <li><strong>Legitimate interests</strong> — security, fraud prevention, product improvement</li>
        <li><strong>Consent</strong> — where required (for example certain cookies or marketing)</li>
        <li><strong>Legal obligation</strong> — when we must retain or disclose information by law</li>
      </ul>

      <h2>5. How we share information</h2>
      <p>We do not sell personal information. We may share information with:</p>
      <ul>
        <li><strong>Service providers</strong> who host infrastructure, email, analytics, or auth (bound by confidentiality)</li>
        <li><strong>Customers</strong> — risk decisions and verification results for traffic on their properties</li>
        <li><strong>Professional advisors</strong> (legal, accounting) under confidentiality</li>
        <li><strong>Authorities</strong> when required by law or to protect rights, safety, and security</li>
        <li><strong>Business transfers</strong> in connection with a merger, acquisition, or asset sale</li>
      </ul>

      <h2>6. Data retention</h2>
      <p>
        We retain account data for as long as your account is active and as needed for legitimate
        business and legal purposes. Telemetry and session features used for detection and
        improvement may be retained for limited periods consistent with security and operations,
        then deleted or aggregated. You may request deletion of account data subject to legal holds.
      </p>

      <h2>7. Security</h2>
      <p>
        We implement administrative, technical, and organizational measures designed to protect
        information, including hashed API secrets, access controls, TLS in transit where
        supported, and least-privilege practices. No method of transmission or storage is
        100% secure; customers must protect secret keys and never embed them in browser code.
      </p>

      <h2>8. International transfers</h2>
      <p>
        We may process information in countries other than where you live. Where required,
        we use appropriate safeguards for cross-border transfers.
      </p>

      <h2>9. Your rights</h2>
      <p>
        Depending on your location, you may have rights to access, correct, delete, port,
        or restrict certain personal data, or to object to certain processing. We may verify
        your identity before responding. You may also lodge a complaint with a supervisory
        authority where applicable.
      </p>

      <h2>10. Children</h2>
      <p>
        The Services are not directed to children under 16 (or the age of digital consent
        in your jurisdiction). We do not knowingly collect personal information from children.
      </p>

      <h2>11. Customer responsibilities</h2>
      <p>
        If you use VeilProof on your website or app, you are the controller (or equivalent)
        for your visitors&apos; data. You must provide required notices, obtain consents where
        needed, and configure allowed domains and keys responsibly.
      </p>

      <h2>12. Changes</h2>
      <p>
        We may update this Policy from time to time. We will post the revised version with
        an updated &quot;Last updated&quot; date. Continued use of the Services after changes
        become effective constitutes acceptance of the updated Policy.
      </p>

      <h2>13. Contact</h2>
      <p>
        VeilProof — Privacy<br />
        Web: <a href="/">veilproof</a>
      </p>
    </LegalPage>
  );
}
