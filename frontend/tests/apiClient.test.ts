import { describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, buildUrl } from '../src/services/apiClient'
import { createAgentXApi } from '../src/services/agentxApi'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('buildUrl', () => {
  it('joins base and path and encodes repeated query values', () => {
    expect(buildUrl('http://api.test', '/api/v1/complaints', { status: ['CREATED', 'WARNING'], limit: 5, skip: undefined })).toBe(
      'http://api.test/api/v1/complaints?status=CREATED&status=WARNING&limit=5',
    )
  })
})

describe('ApiClient', () => {
  it('sends JSON and returns the parsed body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 'c1', status: 'CREATED' }, 201))
    const api = createAgentXApi(new ApiClient('http://api.test', fetchMock))

    const result = await api.createComplaint({ citizen_input: 'Streetlight not working' })

    expect(result).toEqual({ id: 'c1', status: 'CREATED' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://api.test/api/v1/complaints')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ citizen_input: 'Streetlight not working' })
    expect(init.headers['Content-Type']).toBe('application/json')
  })

  it('turns the backend error format into an ApiError', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'validation_error',
            message: 'Request validation failed',
            details: [{ field: 'citizen_input', message: 'too short' }],
            request_id: 'req-1',
          },
        },
        422,
      ),
    )
    const client = new ApiClient('http://api.test', fetchMock)

    const error = await client.post('/api/v1/complaints', {}).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, code: 'validation_error', requestId: 'req-1' })
    expect((error as ApiError).details[0].field).toBe('citizen_input')
  })

  it('reports a network failure clearly', async () => {
    const client = new ApiClient('http://api.test', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(client.get('/health')).rejects.toMatchObject({ status: 0, code: 'network_error' })
  })

  it('handles non-JSON error bodies', async () => {
    const client = new ApiClient('http://api.test', vi.fn().mockResolvedValue(new Response('Bad gateway', { status: 502 })))

    await expect(client.get('/health')).rejects.toMatchObject({ status: 502, code: 'http_error' })
  })
})
