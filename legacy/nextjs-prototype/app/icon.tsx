import { ImageResponse } from 'next/og'

// Metadata para o favicon
export const size = {
  width: 32,
  height: 32,
}
export const contentType = 'image/png'

/**
 * Gera um favicon simples com as letras "LA" em fundo azul escuro
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 20,
          background: '#1D4ED8', // blue-700
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          color: 'white',
        }}
      >
        LA
      </div>
    ),
    {
      width: 32,
      height: 32,
    }
  )
}
