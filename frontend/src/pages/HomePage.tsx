import { useNavigate } from 'react-router-dom'
import { Mic, Heart } from 'lucide-react'

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            VoxDocs
          </h1>
          <p className="text-xl text-gray-600">
            Sprachgesteuerte Dokumentation für Gesundheitsberufe
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Dental Documentation Card */}
          <div
            onClick={() => navigate('/dental')}
            className="bg-white rounded-2xl shadow-xl p-8 cursor-pointer transform transition-all hover:scale-105 hover:shadow-2xl border-2 border-transparent hover:border-blue-500"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mb-6">
                <Mic className="w-10 h-10 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Zahnarzt Dokumentation
              </h2>
              <p className="text-gray-600 mb-6">
                Sprachgesteuerte Behandlungsdokumentation für Zahnarztpraxen.
                Schnelle Erfassung nach jedem Termin.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                  Spracherkennung
                </span>
                <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                  Behandlungsraum
                </span>
                <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                  Training
                </span>
              </div>
            </div>
          </div>

          {/* Nursing Care Documentation Card */}
          <div
            onClick={() => navigate('/nursing/appointment')}
            className="bg-white rounded-2xl shadow-xl p-8 cursor-pointer transform transition-all hover:scale-105 hover:shadow-2xl border-2 border-transparent hover:border-green-500"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6">
                <Heart className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Pflegedienst Dokumentation
              </h2>
              <p className="text-gray-600 mb-6">
                Multilinguale Dokumentation für ambulante Pflegedienste.
                Sprachaufnahmen in beliebiger Sprache, Ausgabe auf Deutsch.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                  Multilingual
                </span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                  Foto + Audio
                </span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                  TTS Vorlesung
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>🔒 100% lokal • DSGVO-konform • Keine Cloud</p>
        </div>
      </div>
    </div>
  )
}
