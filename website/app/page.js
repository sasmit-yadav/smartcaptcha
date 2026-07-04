'use client';

import { useState, useEffect } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { 
  Shield, 
  Zap, 
  Code, 
  Lock, 
  Brain, 
  Globe, 
  BarChart3, 
  ArrowRight,
  CheckCircle2,
  XCircle,
  Activity,
  TrendingUp,
  Cpu,
  Eye,
  MousePointer2,
  Keyboard,
  Scroll,
  Bot,
  User,
  Sparkles,
  ArrowDown
} from 'lucide-react';

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();
  const heroOpacity = useTransform(scrollY, [0, 300], [1, 0]);
  const heroY = useTransform(scrollY, [0, 300], [0, 100]);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'glass-strong py-4' : 'py-6'
      }`}>
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2"
          >
            <Shield className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold">SmartCaptcha</span>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="hidden md:flex items-center gap-8"
          >
            {['Features', 'Developers', 'Documentation', 'API', 'Pricing'].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-textSecondary hover:text-text transition-colors text-sm font-medium"
              >
                {item}
              </a>
            ))}
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4"
          >
            <button 
              onClick={() => window.location.href = '/dashboard'}
              className="text-textSecondary hover:text-text transition-colors text-sm font-medium"
            >
              Sign In
            </button>
            <button 
              onClick={() => window.location.href = '/dashboard'}
              className="bg-primary hover:bg-primaryDark text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              Get Started
            </button>
          </motion.div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent" />
        
        <motion.div 
          style={{ opacity: heroOpacity, y: heroY }}
          className="max-w-7xl mx-auto relative"
        >
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="inline-flex items-center gap-2 bg-surface2 border border-border rounded-full px-4 py-2 mb-6"
              >
                <Sparkles className="w-4 h-4 text-primary" />
                <span className="text-sm text-textSecondary">AI-Powered Security</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-5xl md:text-6xl lg:text-7xl font-bold leading-tight mb-6"
              >
                Stop Bots Without{' '}
                <span className="text-gradient">Frustrating Humans</span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-xl text-textSecondary mb-8 max-w-lg"
              >
                Forget traffic lights and alphabet puzzles. SmartCaptcha uses behavioral telemetry and machine learning to detect bots invisibly, in real-time.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="flex flex-wrap gap-4"
              >
                <button 
                  onClick={() => window.location.href = '/dashboard'}
                  className="bg-primary hover:bg-primaryDark text-white px-8 py-4 rounded-lg font-medium transition-all hover:scale-105 flex items-center gap-2"
                >
                  Get Started
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button className="bg-surface2 hover:bg-surface text-text px-8 py-4 rounded-lg font-medium transition-colors border border-border">
                  View Documentation
                </button>
              </motion.div>
            </div>

            {/* Animated Product Preview */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 }}
              className="relative"
            >
              <div className="glass-strong rounded-2xl p-6 border border-border">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="text-sm text-textSecondary mb-1">Risk Score</div>
                    <div className="text-3xl font-bold text-gradient">12/100</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm text-textSecondary">Live</span>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="bg-surface2 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-textSecondary">Bot Probability</span>
                      <span className="text-sm font-medium">8%</span>
                    </div>
                    <div className="h-2 bg-surface rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: '8%' }}
                        transition={{ delay: 1, duration: 1 }}
                        className="h-full bg-green-500 rounded-full"
                      />
                    </div>
                  </div>

                  <div className="bg-surface2 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-textSecondary">Human Confidence</span>
                      <span className="text-sm font-medium">94%</span>
                    </div>
                    <div className="h-2 bg-surface rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: '94%' }}
                        transition={{ delay: 1.2, duration: 1 }}
                        className="h-full bg-primary rounded-full"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-surface2 rounded-lg p-3 text-center">
                      <MousePointer2 className="w-5 h-5 text-primary mx-auto mb-1" />
                      <div className="text-xs text-textSecondary">Mouse</div>
                      <div className="text-sm font-medium">Natural</div>
                    </div>
                    <div className="bg-surface2 rounded-lg p-3 text-center">
                      <Keyboard className="w-5 h-5 text-primary mx-auto mb-1" />
                      <div className="text-xs text-textSecondary">Keyboard</div>
                      <div className="text-sm font-medium">Human</div>
                    </div>
                    <div className="bg-surface2 rounded-lg p-3 text-center">
                      <Scroll className="w-5 h-5 text-primary mx-auto mb-1" />
                      <div className="text-xs text-textSecondary">Scroll</div>
                      <div className="text-sm font-medium">Smooth</div>
                    </div>
                  </div>
                </div>

                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.5 }}
                  className="mt-4 flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-lg p-3"
                >
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <span className="text-sm text-green-400">Human Verified</span>
                </motion.div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* Trust Section */}
      <section className="py-20 px-6 border-y border-border">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
            {[
              'Enterprise Ready',
              'Privacy First',
              'Real-Time AI',
              'SDK Driven',
              'Behavioral Detection',
              'High Accuracy'
            ].map((item, index) => (
              <motion.div
                key={item}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="text-center"
              >
                <div className="text-textSecondary text-sm font-medium">{item}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Built for Modern Security
            </h2>
            <p className="text-xl text-textSecondary max-w-2xl mx-auto">
              Advanced behavioral analysis powered by machine learning
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Brain, title: 'Behavioral AI Detection', desc: 'Analyze mouse movements, keyboard dynamics, and scroll patterns to distinguish humans from bots.' },
              { icon: Zap, title: 'Real-Time Risk Scoring', desc: 'Get instant risk scores with confidence intervals. No waiting, no blocking legitimate users.' },
              { icon: Eye, title: 'Invisible Verification', desc: 'Users never see a CAPTCHA. Verification happens silently in the background.' },
              { icon: Globe, title: 'Cross Platform SDK', desc: 'Works seamlessly across web, mobile, and desktop applications with unified API.' },
              { icon: Code, title: 'Developer Friendly APIs', desc: 'Simple integration with comprehensive documentation and SDKs for all major platforms.' },
              { icon: BarChart3, title: 'Advanced Telemetry Engine', desc: 'Collect rich behavioral data while respecting privacy. GDPR and CCPA compliant.' },
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ scale: 1.02 }}
                className="glass rounded-2xl p-6 hover:border-primary/50 transition-colors cursor-pointer group"
              >
                <feature.icon className="w-8 h-8 text-primary mb-4 group-hover:scale-110 transition-transform" />
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-textSecondary">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how" className="py-32 px-6 bg-surface2/50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-xl text-textSecondary max-w-2xl mx-auto">
              Four simple steps to invisible security
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              { step: '01', title: 'Integrate SDK', desc: 'Add a single line of code to your application' },
              { step: '02', title: 'Collect Signals', desc: 'Behavioral data is collected invisibly' },
              { step: '03', title: 'AI Analysis', desc: 'Machine learning models analyze patterns' },
              { step: '04', title: 'Smart Decision', desc: 'Allow, challenge, or block based on risk' },
            ].map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="relative"
              >
                <div className="text-6xl font-bold text-textSecondary/20 mb-4">{item.step}</div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-textSecondary">{item.desc}</p>
                {index < 3 && (
                  <ArrowDown className="absolute right-0 top-20 w-6 h-6 text-border hidden md:block" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* SDK Section */}
      <section id="sdk" className="py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Simple Integration
            </h2>
            <p className="text-xl text-textSecondary max-w-2xl mx-auto">
              Get started in minutes with our SDKs
            </p>
          </motion.div>

          <div className="glass-strong rounded-2xl p-8 border border-border">
            <div className="flex gap-4 mb-6">
              {['JavaScript', 'React', 'Vue', 'HTML'].map((lang) => (
                <button
                  key={lang}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-surface2 text-text"
                >
                  {lang}
                </button>
              ))}
            </div>

            <div className="bg-surface rounded-xl p-6 font-mono text-sm overflow-x-auto">
              <pre className="text-textSecondary">
                <code>{`npm install nextcaptcha-sdk

import NextCaptcha from 'nextcaptcha-sdk';

NextCaptcha.init({
  apiKey: 'your-api-key',
  endpoint: 'https://next-captcha-sdk.onrender.com'
});

NextCaptcha.getDecision((result) => {
  if (result.action === 'block') {
    // Block the action
  } else {
    // Allow the action
  }
});`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-accent/20" />
        <div className="max-w-4xl mx-auto text-center relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Start Protecting Your Application Today
            </h2>
            <p className="text-xl text-textSecondary mb-8 max-w-2xl mx-auto">
              Join thousands of developers who trust SmartCaptcha for invisible, intelligent bot protection.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <button 
                onClick={() => window.location.href = '/dashboard'}
                className="bg-primary hover:bg-primaryDark text-white px-8 py-4 rounded-lg font-medium transition-all hover:scale-105 flex items-center gap-2"
              >
                Get Started Free
                <ArrowRight className="w-4 h-4" />
              </button>
              <button className="bg-surface2 hover:bg-surface text-text px-8 py-4 rounded-lg font-medium transition-colors border border-border">
                View Documentation
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-16 px-6 border-t border-border">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-5 gap-12 mb-12">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-8 h-8 text-primary" />
                <span className="text-xl font-bold">SmartCaptcha</span>
              </div>
              <p className="text-textSecondary max-w-sm">
                AI-powered behavioral CAPTCHA that stops bots without frustrating humans.
              </p>
            </div>

            {[
              { title: 'Product', links: ['Features', 'Pricing', 'Security', 'Roadmap'] },
              { title: 'Developers', links: ['Documentation', 'API Reference', 'SDKs', 'Examples'] },
              { title: 'Resources', links: ['Blog', 'Case Studies', 'Support', 'Status'] },
              { title: 'Company', links: ['About', 'Careers', 'Contact', 'Legal'] },
            ].map((col) => (
              <div key={col.title}>
                <h4 className="font-semibold mb-4">{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map((link) => (
                    <li key={link}>
                      <a href="#" className="text-textSecondary hover:text-text transition-colors text-sm">
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-border">
            <p className="text-textSecondary text-sm">
              © 2024 SmartCaptcha. All rights reserved.
            </p>
            <div className="flex gap-6 mt-4 md:mt-0">
              <a href="#" className="text-textSecondary hover:text-text transition-colors text-sm">
                Privacy Policy
              </a>
              <a href="#" className="text-textSecondary hover:text-text transition-colors text-sm">
                Terms of Service
              </a>
              <a href="#" className="text-textSecondary hover:text-text transition-colors text-sm">
                GitHub
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
