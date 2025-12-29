import React, { useState } from 'react';

export default function Pricing() {
  const [billingCycle, setBillingCycle] = useState('monthly');

  const plans = {
    starter: {
      name: 'Starter',
      tagline: 'Perfect for individuals',
      monthly: 599,
      quarterly: 1599,
      yearly: 5999,
      features: [
        '50 measurements per day',
        '6 months data retention',
        'Basic AI accuracy',
        'Export as PDF/CSV',
        'Email support (48h)',
        'Mobile friendly'
      ]
    },
    professional: {
      name: 'Professional',
      tagline: 'Best for growing businesses',
      monthly: 1999,
      quarterly: 5399,
      yearly: 19999,
      popular: true,
      features: [
        '500 measurements per day',
        '2 years data retention',
        'Advanced AI accuracy',
        'API access included',
        'Chat support (24h)',
        '5 team members',
        'Priority processing'
      ]
    },
    enterprise: {
      name: 'Enterprise',
      tagline: 'For large organizations',
      monthly: 4999,
      quarterly: 13499,
      yearly: 49999,
      features: [
        'Unlimited measurements',
        'Lifetime data retention',
        'Premium AI accuracy',
        'Advanced API + Webhooks',
        'Dedicated support (2h)',
        'Unlimited team members',
        'White label branding',
        'Custom integrations'
      ]
    }
  };

  const handleSubscribe = (tier) => {
    // Redirect to payment page with tier info
    window.location.href = `/payment?tier=${tier}&cycle=${billingCycle}`;
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '40px 20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '50px' }}>
        <h1 style={{ fontSize: '3em', color: 'white', marginBottom: '10px' }}>💎 Upgrade to Premium</h1>
        <p style={{ fontSize: '1.2em', color: 'rgba(255,255,255,0.9)', marginBottom: '30px' }}>
          Get AI-powered body measurements with lifetime access
        </p>
        
        {/* Billing Toggle */}
        <div style={{
          display: 'inline-flex',
          background: 'rgba(255,255,255,0.2)',
          borderRadius: '12px',
          padding: '5px'
        }}>
          {['monthly', 'quarterly', 'yearly'].map((cycle) => (
            <button
              key={cycle}
              onClick={() => setBillingCycle(cycle)}
              style={{
                padding: '12px 24px',
                border: 'none',
                borderRadius: '8px',
                background: billingCycle === cycle ? 'white' : 'transparent',
                color: billingCycle === cycle ? '#667eea' : 'white',
                fontWeight: 'bold',
                cursor: 'pointer',
                transition: 'all 0.3s',
                textTransform: 'capitalize'
              }}
            >
              {cycle}
              {cycle === 'yearly' && <span style={{ fontSize: '0.8em', marginLeft: '5px' }}>🔥 Save 17%</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Pricing Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '30px',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        {Object.entries(plans).map(([key, plan]) => (
          <div
            key={key}
            style={{
              background: plan.popular ? 'white' : 'rgba(255,255,255,0.15)',
              backdropFilter: 'blur(10px)',
              borderRadius: '20px',
              padding: '30px',
              position: 'relative',
              border: plan.popular ? '3px solid #48bb78' : '2px solid rgba(255,255,255,0.2)',
              transform: plan.popular ? 'scale(1.05)' : 'scale(1)',
              transition: 'all 0.3s',
              boxShadow: plan.popular ? '0 20px 40px rgba(0,0,0,0.3)' : 'none'
            }}
          >
            {plan.popular && (
              <div style={{
                position: 'absolute',
                top: '-15px',
                left: '50%',
                transform: 'translateX(-50%)',
                background: '#48bb78',
                color: 'white',
                padding: '8px 20px',
                borderRadius: '20px',
                fontSize: '0.9em',
                fontWeight: 'bold'
              }}>
                🌟 MOST POPULAR
              </div>
            )}

            <h2 style={{
              fontSize: '2em',
              marginBottom: '5px',
              color: plan.popular ? '#667eea' : 'white'
            }}>
              {plan.name}
            </h2>
            <p style={{
              fontSize: '1em',
              marginBottom: '20px',
              color: plan.popular ? '#666' : 'rgba(255,255,255,0.8)'
            }}>
              {plan.tagline}
            </p>

            <div style={{ marginBottom: '25px' }}>
              <span style={{
                fontSize: '3em',
                fontWeight: 'bold',
                color: plan.popular ? '#667eea' : 'white'
              }}>
                ₹{plan[billingCycle]}
              </span>
              <span style={{
                fontSize: '1em',
                color: plan.popular ? '#999' : 'rgba(255,255,255,0.7)'
              }}>
                /{billingCycle === 'monthly' ? 'month' : billingCycle === 'quarterly' ? 'quarter' : 'year'}
              </span>
            </div>

            <button
              onClick={() => handleSubscribe(key)}
              style={{
                width: '100%',
                padding: '15px',
                background: plan.popular ? '#667eea' : '#48bb78',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                fontSize: '1.1em',
                fontWeight: 'bold',
                cursor: 'pointer',
                marginBottom: '25px',
                transition: 'all 0.3s'
              }}
            >
              Subscribe Now →
            </button>

            <div style={{ borderTop: `2px solid ${plan.popular ? '#eee' : 'rgba(255,255,255,0.2)'}`, paddingTop: '20px' }}>
              <h4 style={{
                fontSize: '1em',
                marginBottom: '15px',
                color: plan.popular ? '#333' : 'white'
              }}>
                ✨ What's Included:
              </h4>
              <ul style={{
                listStyle: 'none',
                padding: 0,
                margin: 0
              }}>
                {plan.features.map((feature, idx) => (
                  <li
                    key={idx}
                    style={{
                      padding: '8px 0',
                      fontSize: '0.95em',
                      color: plan.popular ? '#555' : 'rgba(255,255,255,0.9)'
                    }}
                  >
                    ✓ {feature}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Note */}
      <div style={{
        textAlign: 'center',
        marginTop: '50px',
        color: 'rgba(255,255,255,0.8)',
        fontSize: '0.95em'
      }}>
        <p>🔒 Secure payment via UPI/Google Pay • Cancel anytime • No hidden fees</p>
        <p style={{ marginTop: '10px' }}>💳 Direct bank transfer • ₹0 payment gateway fees</p>
      </div>
    </div>
  );
}
