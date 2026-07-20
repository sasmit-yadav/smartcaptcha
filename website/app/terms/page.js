import LegalPage from '../../components/chrome/LegalPage';

export const metadata = {
  title: 'Terms of Service — VeilProof',
  description: 'Terms governing use of VeilProof websites, SDKs, APIs, and bot-detection services.',
};

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service" updated="July 20, 2026">
      <p>
        These Terms of Service (&quot;Terms&quot;) form a binding agreement between you
        (&quot;Customer,&quot; &quot;you,&quot; or &quot;your&quot;) and VeilProof (&quot;VeilProof,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;)
        governing access to and use of our websites, dashboards, documentation, SDKs, APIs,
        and related services (the &quot;Services&quot;).
      </p>
      <p>
        By creating an account, obtaining API keys, or using the Services, you agree to these Terms.
        If you are accepting on behalf of a company, you represent that you have authority to bind
        that company. If you do not agree, do not use the Services.
      </p>

      <h2>1. The Services</h2>
      <p>
        VeilProof provides invisible behavioral bot-detection capabilities. The browser SDK
        collects signals and requests a risk decision; your systems must verify tokens
        server-side using a secret key before trusting a request. Browser-side output alone
        is not a trust boundary.
      </p>
      <p>
        We may modify, suspend, or discontinue features with reasonable notice when practical.
        Beta or free-tier features may change or end without the same notice commitments as
        paid production SLAs (if any).
      </p>

      <h2>2. Accounts and API keys</h2>
      <ul>
        <li>You must provide accurate account information and keep credentials confidential.</li>
        <li>Site keys may be used in client environments; secret keys must remain server-side only.</li>
        <li>You are responsible for all activity under your keys and for configuring allowed domains.</li>
        <li>We may revoke keys or suspend accounts for abuse, security risk, or Terms violations.</li>
      </ul>

      <h2>3. Acceptable use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Probe, attack, or disrupt the Services except via authorized security research we approve</li>
        <li>Bypass or interfere with rate limits, authentication, or domain restrictions</li>
        <li>Use the Services to violate law, harm others, or process illegal content</li>
        <li>Resell or sublicense the Services except as expressly permitted in writing</li>
        <li>Reverse engineer the Services except where mandatory law prohibits that restriction</li>
        <li>Misrepresent risk outcomes or remove attribution required in documentation (if any)</li>
      </ul>

      <h2>4. Customer data and privacy</h2>
      <p>
        You retain rights to your account content and customer configuration. You grant VeilProof
        a limited license to process data as needed to provide and secure the Services.
        Our <a href="/privacy">Privacy Policy</a> explains how we handle personal information.
        You are responsible for lawful use of the SDK on your properties, including notices
        and consents owed to your end users.
      </p>

      <h2>5. Intellectual property</h2>
      <p>
        VeilProof and its licensors own the Services, including software, models, documentation,
        branding, and related IP. Except for the limited rights to use the Services under these
        Terms, no rights are granted by implication. Feedback you provide may be used by us
        without obligation to you.
      </p>

      <h2>6. Third-party services</h2>
      <p>
        The Services may integrate with third parties (for example cloud hosting or Google sign-in).
        Their terms and privacy practices apply to their portions of the stack. We are not
        responsible for third-party services we do not control.
      </p>

      <h2>7. Fees (if applicable)</h2>
      <p>
        Paid plans, if offered, will be described at purchase or in an order form. Fees are
        non-refundable except where required by law or expressly stated. Failure to pay may
        result in suspension. Taxes are your responsibility unless we state otherwise.
      </p>

      <h2>8. Confidentiality</h2>
      <p>
        Each party may receive non-public information from the other. The receiving party will
        protect it with reasonable care and use it only to perform under these Terms, except
        for information that is public, independently developed, or required to be disclosed by law.
      </p>

      <h2>9. Disclaimers</h2>
      <p>
        THE SERVICES ARE PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE.&quot; TO THE MAXIMUM EXTENT
        PERMITTED BY LAW, WE DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING
        MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
      </p>
      <p>
        Bot detection is probabilistic. We do not warrant that every bot will be blocked or
        that every human will always be allowed. You must implement server-side verification
        and your own risk policies. Outages, latency, and false positives/negatives may occur.
      </p>

      <h2>10. Limitation of liability</h2>
      <p>
        TO THE MAXIMUM EXTENT PERMITTED BY LAW, VEILPROOF WILL NOT BE LIABLE FOR INDIRECT,
        INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR ANY LOSS OF
        PROFITS, REVENUE, DATA, OR GOODWILL, EVEN IF ADVISED OF THE POSSIBILITY.
      </p>
      <p>
        OUR AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THE SERVICES WILL NOT EXCEED
        THE AMOUNTS YOU PAID TO VEILPROOF FOR THE SERVICES IN THE TWELVE (12) MONTHS BEFORE
        THE CLAIM (OR USD $100 IF YOU HAVE NOT PAID FEES).
      </p>

      <h2>11. Indemnity</h2>
      <p>
        You will defend and indemnify VeilProof against claims arising from your use of the
        Services, your sites/apps, your end-user notices, or your violation of these Terms
        or applicable law, except to the extent caused by our willful misconduct.
      </p>

      <h2>12. Suspension and termination</h2>
      <p>
        You may stop using the Services at any time. We may suspend or terminate access for
        breach, risk, non-payment, or prolonged inactivity. Upon termination, your license
        ends and you must cease use of SDKs and keys. Sections that by nature should survive
        (including IP, disclaimers, liability limits, and indemnity) will survive.
      </p>

      <h2>13. Governing law</h2>
      <p>
        These Terms are governed by the laws applicable in the jurisdiction where VeilProof
        principally operates, without regard to conflict-of-law rules, unless mandatory
        consumer protections in your country require otherwise. Courts in that jurisdiction
        will have exclusive venue, subject to those mandatory protections.
      </p>

      <h2>14. Changes</h2>
      <p>
        We may update these Terms by posting a revised version with a new &quot;Last updated&quot;
        date. Material changes for paid customers may be communicated by email or dashboard
        notice where practical. Continued use after the effective date constitutes acceptance.
      </p>

      <h2>15. Contact</h2>
      <p>
        VeilProof — Legal<br />
        Privacy: <a href="/privacy">Privacy Policy</a>
      </p>
    </LegalPage>
  );
}
