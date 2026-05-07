import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { exchangeCodeForToken, hasAccessToken } from '../../utils/oauth';

export const AuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const urlParams = new URLSearchParams(location.search);
      const code = urlParams.get('code');
      const state = urlParams.get('state');
      const oauthError = urlParams.get('error');

      if (oauthError) {
        const desc = urlParams.get('error_description') ?? oauthError;
        setError(`Authorization denied: ${desc}`);
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received');
        setTimeout(() => navigate('/login'), 2000);
        return;
      }

      try {
        await exchangeCodeForToken(code, state ?? '');
        navigate('/', { replace: true });
      } catch (err: any) {
        console.error('Token exchange error:', err);
        setError(err.message ?? 'Authentication failed');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [navigate, location]);

  if (error) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="100vh">
        <Typography color="error" variant="h6">{error}</Typography>
        <Typography variant="body2" mt={2}>Redirecting to login…</Typography>
      </Box>
    );
  }

  return (
    <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="100vh">
      <CircularProgress size={60} />
      <Typography variant="h6" mt={2}>Completing authentication…</Typography>
    </Box>
  );
};