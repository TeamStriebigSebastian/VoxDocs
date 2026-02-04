
export interface FetchOptions extends RequestInit {
    skipAuth?: boolean;
}

export const fetchWithAuth = async (url: string, options: FetchOptions = {}): Promise<Response> => {
    let token = localStorage.getItem('access_token');

    // Prepare headers
    const headers = new Headers(options.headers || {});

    // Add Auth header if not skipped and token exists
    if (!options.skipAuth && token) {
        // Only set if not already set
        if (!headers.has('Authorization')) {
            headers.set('Authorization', `Bearer ${token}`);
        }
    }

    let res = await fetch(url, { ...options, headers });

    // Handle 401 Unauthorized
    if (res.status === 401 && !options.skipAuth) {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
            try {
                // Attempt to refresh token
                const refreshRes = await fetch('/api/auth/refresh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken })
                });

                if (refreshRes.ok) {
                    const data = await refreshRes.json();
                    const newToken = data.access_token;
                    const newRefreshToken = data.refresh_token;

                    // Update Storage
                    localStorage.setItem('access_token', newToken);
                    localStorage.setItem('refresh_token', newRefreshToken);

                    // Dispatch custom event for UI updates (e.g. AuthContext)
                    window.dispatchEvent(new Event('auth:token-refreshed'));

                    // Retry original request with new token
                    headers.set('Authorization', `Bearer ${newToken}`);
                    res = await fetch(url, { ...options, headers });
                } else {
                    console.warn('Token refresh failed: Server rejected refresh token.');
                    // Optional: Dispatch logout event
                    // window.dispatchEvent(new Event('auth:logout'));
                }
            } catch (e) {
                console.error('Token refresh error:', e);
            }
        }
    }

    return res;
};
